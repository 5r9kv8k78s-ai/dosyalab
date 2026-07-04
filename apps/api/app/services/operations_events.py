"""Privacy-safe operational event tracking for the future DosyaLab Admin
Panel — answers questions like "how many conversions succeeded/failed",
"which tools are used most", "how long do conversions take" without ever
storing anything that identifies a user or their file content.

Explicitly never recorded, by construction of the `OperationsEvent` shape
below: filenames, file content, document text, user names/emails, or a raw
persistent IP address. Callers cannot accidentally widen this — there is no
field to put such data in.

In-memory only for V1 (see `InMemoryOperationsEventStore`) — no database
exists yet in this repository (see app/services/jobs.py's own "single
process, in-memory" precedent). Events are lost on restart and are
per-replica if this API ever runs more than one instance; this is an
architecture bridge for the Admin Panel's future queries, not production
analytics persistence.
"""

import logging
import threading
import time
import uuid
from collections import Counter, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)

EventType = Literal["conversion", "rate_limit_rejection"]

# One row per attempt, holding its *final* outcome — not a multi-row
# started/finished lifecycle. A conversion is only ever recorded once,
# right when its outcome becomes known (see instrumentation in
# run_conversion_job and the convert.py endpoints), which keeps Admin Panel
# queries a simple GROUP BY status instead of needing to correlate a
# "started" row with a later "finished" row that might never arrive.
EventStatus = Literal["success", "failure", "validation_rejected"]

# Broad, low-cardinality operational categories — never a raw extension,
# which would let filenames leak back in via cardinality (e.g. every
# distinct extension combination) and isn't needed to answer "what file
# families are processed".
InputFamily = Literal["pdf", "document", "spreadsheet", "image", "mixed", "unknown"]

# Stable categories only — never the raw exception message (which can
# contain incidental detail not meant to be an analytics dimension).
ErrorCode = Literal[
    "invalid_file_type",
    "invalid_file_count",
    "file_too_large",
    "batch_too_large",
    "conversion_failed",
    "rate_limited",
    "validation_failed",
]


@dataclass(frozen=True)
class OperationsEvent:
    event_id: str
    event_type: EventType
    tool_slug: str | None
    status: EventStatus
    file_count: int
    input_family: InputFamily
    duration_ms: int | None
    error_code: ErrorCode | None
    created_at: datetime


class OperationsEventStore(Protocol):
    """Abstraction the future Admin Panel API queries against — a
    persistent (e.g. Postgres-backed) implementation can replace
    `InMemoryOperationsEventStore` later without changing any caller."""

    def record(
        self,
        *,
        event_type: EventType,
        tool_slug: str | None,
        status: EventStatus,
        file_count: int,
        input_family: InputFamily,
        duration_ms: int | None,
        error_code: ErrorCode | None,
    ) -> None: ...

    def summarize_by_status(self) -> dict[str, int]: ...
    def summarize_by_tool(self) -> dict[str, int]: ...
    def summarize_by_error(self) -> dict[str, int]: ...


class InMemoryOperationsEventStore:
    """Process-local, in-memory `OperationsEventStore` — thread-safe, with
    bounded retention (by count and by age) so this can never grow without
    limit. Data does not survive a process restart and is not shared across
    replicas if the API is ever scaled horizontally.
    """

    def __init__(self, max_count: int, retention_seconds: int) -> None:
        self._max_count = max_count
        self._retention_seconds = retention_seconds
        self._events: deque[OperationsEvent] = deque()
        self._lock = threading.Lock()

    def record(
        self,
        *,
        event_type: EventType,
        tool_slug: str | None,
        status: EventStatus,
        file_count: int,
        input_family: InputFamily,
        duration_ms: int | None,
        error_code: ErrorCode | None,
    ) -> None:
        event = OperationsEvent(
            event_id=uuid.uuid4().hex,
            event_type=event_type,
            tool_slug=tool_slug,
            status=status,
            file_count=file_count,
            input_family=input_family,
            duration_ms=duration_ms,
            error_code=error_code,
            created_at=datetime.now(UTC),
        )
        with self._lock:
            self._events.append(event)
            self._prune_locked()

    def summarize_by_status(self) -> dict[str, int]:
        with self._lock:
            self._prune_locked()
            return dict(Counter(event.status for event in self._events))

    def summarize_by_tool(self) -> dict[str, int]:
        with self._lock:
            self._prune_locked()
            return dict(
                Counter(event.tool_slug for event in self._events if event.tool_slug is not None)
            )

    def summarize_by_error(self) -> dict[str, int]:
        with self._lock:
            self._prune_locked()
            return dict(
                Counter(event.error_code for event in self._events if event.error_code is not None)
            )

    def _prune_locked(self) -> None:
        """Drops events past the retention window, then trims to
        `max_count` — called on every write and read rather than via a
        background scheduler, since pruning on access is sufficient for
        this V1 volume and avoids an extra always-running task."""
        cutoff = time.time() - self._retention_seconds
        while self._events and self._events[0].created_at.timestamp() < cutoff:
            self._events.popleft()
        while len(self._events) > self._max_count:
            self._events.popleft()


# Every tool's *input* family is fixed and known statically — mirrors the
# frontend's `fileType` grouping (apps/web/lib/tools.ts) without importing
# across the API boundary. Kept here (not in conversion.py) so this module
# has no dependency on conversion.py, only the reverse.
_DOCUMENT_INPUT_SLUGS = frozenset({"docx-to-pdf"})
_IMAGE_INPUT_SLUGS = frozenset({"images-to-pdf"})
# Every other current tool slug takes a single PDF (or a PDF batch, for
# merge-pdf) as input — spreadsheet/mixed have no input tool yet, but the
# category exists for forward compatibility with the Admin Panel schema.


def classify_input_family(tool_slug: str | None) -> InputFamily:
    if tool_slug is None:
        return "unknown"
    if tool_slug in _DOCUMENT_INPUT_SLUGS:
        return "document"
    if tool_slug in _IMAGE_INPUT_SLUGS:
        return "image"
    return "pdf"


_store: InMemoryOperationsEventStore | None = None
_store_lock = threading.Lock()


def get_operations_event_store() -> InMemoryOperationsEventStore:
    """Lazily builds the process-wide singleton from current settings —
    mirrors `app.services.jobs.job_store`'s module-level-singleton pattern."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                settings = get_settings()
                _store = InMemoryOperationsEventStore(
                    max_count=settings.operations_events_max_count,
                    retention_seconds=settings.operations_events_retention_seconds,
                )
    return _store


def record_operations_event(
    *,
    event_type: EventType,
    tool_slug: str | None,
    status: EventStatus,
    file_count: int,
    input_family: InputFamily,
    duration_ms: int | None,
    error_code: ErrorCode | None,
) -> None:
    """Safe entry point every caller should use instead of the store
    directly — respects `OPERATIONS_EVENTS_ENABLED` and never lets a
    tracking failure propagate into the actual conversion request/response
    (logged instead, per the "instrumentation must not become a hard
    dependency for conversion success" requirement).
    """
    settings = get_settings()
    if not settings.operations_events_enabled:
        return

    try:
        get_operations_event_store().record(
            event_type=event_type,
            tool_slug=tool_slug,
            status=status,
            file_count=file_count,
            input_family=input_family,
            duration_ms=duration_ms,
            error_code=error_code,
        )
    except Exception:
        logger.warning("operations_events.record_failed", exc_info=True)
