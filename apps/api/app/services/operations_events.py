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
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal, Protocol

from app.core.config import Settings, get_settings

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


@dataclass(frozen=True)
class OverviewMetrics:
    """See `classify_input_family`'s neighbors for the precise definition
    of each field — computed identically by every store implementation:

    - conversion_attempts: every `event_type="conversion"` event, any status.
    - successful_conversions / failed_conversions / validation_rejections:
      conversion events with status success / failure / validation_rejected.
    - rate_limit_rejections: every `event_type="rate_limit_rejection"` event.
    - success_rate: successful_conversions / conversion_attempts, or 0.0 if
      there were no attempts (never divides by zero).
    - average_duration_ms: mean `duration_ms` over conversion events where
      it's not null (success + failure; validation_rejected has no
      duration since no conversion work ran).
    - total_files_processed: sum of `file_count` over *successful*
      conversions only — files that were actually converted, not merely
      uploaded and rejected.
    """

    conversion_attempts: int
    successful_conversions: int
    failed_conversions: int
    validation_rejections: int
    rate_limit_rejections: int
    success_rate: float
    average_duration_ms: float | None
    total_files_processed: int


@dataclass(frozen=True)
class DailyActivity:
    day: date
    attempts: int
    successes: int
    failures_or_rejections: int


@dataclass(frozen=True)
class ToolAggregation:
    tool_slug: str
    attempt_count: int
    success_count: int
    failure_count: int
    success_rate: float
    average_duration_ms: float | None


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

    def get_overview(self, since: datetime) -> OverviewMetrics: ...
    def get_daily_activity(self, since: datetime) -> list[DailyActivity]: ...
    def get_tool_aggregation(self, since: datetime) -> list[ToolAggregation]: ...
    def get_error_aggregation(self, since: datetime) -> list[tuple[str, int]]: ...


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

    def get_overview(self, since: datetime) -> OverviewMetrics:
        with self._lock:
            self._prune_locked()
            events = [e for e in self._events if e.created_at >= since]

        conversions = [e for e in events if e.event_type == "conversion"]
        successes = [e for e in conversions if e.status == "success"]
        failures = [e for e in conversions if e.status == "failure"]
        rejections = [e for e in conversions if e.status == "validation_rejected"]
        rate_limited = [e for e in events if e.event_type == "rate_limit_rejection"]
        durations = [e.duration_ms for e in conversions if e.duration_ms is not None]

        attempts = len(conversions)
        return OverviewMetrics(
            conversion_attempts=attempts,
            successful_conversions=len(successes),
            failed_conversions=len(failures),
            validation_rejections=len(rejections),
            rate_limit_rejections=len(rate_limited),
            success_rate=(len(successes) / attempts) if attempts else 0.0,
            average_duration_ms=(sum(durations) / len(durations)) if durations else None,
            total_files_processed=sum(e.file_count for e in successes),
        )

    def get_daily_activity(self, since: datetime) -> list[DailyActivity]:
        with self._lock:
            self._prune_locked()
            events = [
                e for e in self._events if e.created_at >= since and e.event_type == "conversion"
            ]

        by_day: dict[date, dict[str, int]] = defaultdict(lambda: {"a": 0, "s": 0, "f": 0})
        for event in events:
            bucket = by_day[event.created_at.date()]
            bucket["a"] += 1
            if event.status == "success":
                bucket["s"] += 1
            else:
                bucket["f"] += 1

        return [
            DailyActivity(day=day, attempts=v["a"], successes=v["s"], failures_or_rejections=v["f"])
            for day, v in sorted(by_day.items())
        ]

    def get_tool_aggregation(self, since: datetime) -> list[ToolAggregation]:
        with self._lock:
            self._prune_locked()
            events = [
                e
                for e in self._events
                if e.created_at >= since and e.event_type == "conversion" and e.tool_slug
            ]

        by_tool: dict[str, list[OperationsEvent]] = defaultdict(list)
        for event in events:
            by_tool[event.tool_slug].append(event)  # type: ignore[index]

        results = []
        for slug, tool_events in by_tool.items():
            successes = [e for e in tool_events if e.status == "success"]
            failures = [e for e in tool_events if e.status == "failure"]
            durations = [e.duration_ms for e in tool_events if e.duration_ms is not None]
            attempts = len(tool_events)
            results.append(
                ToolAggregation(
                    tool_slug=slug,
                    attempt_count=attempts,
                    success_count=len(successes),
                    failure_count=len(failures),
                    success_rate=(len(successes) / attempts) if attempts else 0.0,
                    average_duration_ms=(sum(durations) / len(durations)) if durations else None,
                )
            )
        return sorted(results, key=lambda r: r.attempt_count, reverse=True)

    def get_error_aggregation(self, since: datetime) -> list[tuple[str, int]]:
        with self._lock:
            self._prune_locked()
            events = [e for e in self._events if e.created_at >= since and e.error_code]

        counts = Counter(e.error_code for e in events)
        return sorted(counts.items(), key=lambda item: item[1], reverse=True)


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


class PostgresOperationsEventStore:
    """Persistent `OperationsEventStore` backed by the `operations_events`
    table (see app/db/models.py, migrations/versions/0001_*). Selected via
    `OPERATIONS_STORE_BACKEND=postgres` — this is the real production
    implementation; `InMemoryOperationsEventStore` above remains for local
    dev/tests or an explicit fallback, never a silent substitute.
    """

    def __init__(self) -> None:
        # Eagerly resolve the engine at store construction (raises
        # `DatabaseNotConfiguredError` immediately if DATABASE_URL is
        # missing) rather than only on the first record/query call.
        from app.db.session import get_engine

        get_engine()

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
        from app.db.models import OperationsEventRow
        from app.db.session import session_scope

        with session_scope() as session:
            session.add(
                OperationsEventRow(
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
            )

    def summarize_by_status(self) -> dict[str, int]:
        from sqlalchemy import func, select

        from app.db.models import OperationsEventRow
        from app.db.session import session_scope

        with session_scope() as session:
            rows = session.execute(
                select(OperationsEventRow.status, func.count()).group_by(
                    OperationsEventRow.status
                )
            ).all()
        return {status: count for status, count in rows}

    def summarize_by_tool(self) -> dict[str, int]:
        from sqlalchemy import func, select

        from app.db.models import OperationsEventRow
        from app.db.session import session_scope

        with session_scope() as session:
            rows = session.execute(
                select(OperationsEventRow.tool_slug, func.count())
                .where(OperationsEventRow.tool_slug.is_not(None))
                .group_by(OperationsEventRow.tool_slug)
            ).all()
        return {slug: count for slug, count in rows}

    def summarize_by_error(self) -> dict[str, int]:
        from sqlalchemy import func, select

        from app.db.models import OperationsEventRow
        from app.db.session import session_scope

        with session_scope() as session:
            rows = session.execute(
                select(OperationsEventRow.error_code, func.count())
                .where(OperationsEventRow.error_code.is_not(None))
                .group_by(OperationsEventRow.error_code)
            ).all()
        return {code: count for code, count in rows}

    def get_overview(self, since: datetime) -> OverviewMetrics:
        from sqlalchemy import func, select

        from app.db.models import OperationsEventRow
        from app.db.session import session_scope

        row = OperationsEventRow
        with session_scope() as session:
            conversions = select(row).where(row.created_at >= since, row.event_type == "conversion")
            attempts = session.scalar(
                select(func.count()).select_from(conversions.subquery())
            ) or 0
            successes = session.scalar(
                select(func.count()).select_from(
                    conversions.where(row.status == "success").subquery()
                )
            ) or 0
            failures = session.scalar(
                select(func.count()).select_from(
                    conversions.where(row.status == "failure").subquery()
                )
            ) or 0
            rejections = session.scalar(
                select(func.count()).select_from(
                    conversions.where(row.status == "validation_rejected").subquery()
                )
            ) or 0
            rate_limited = session.scalar(
                select(func.count()).where(
                    row.created_at >= since, row.event_type == "rate_limit_rejection"
                )
            ) or 0
            # `func.avg(row.duration_ms)`/`func.sum(row.file_count)` reference
            # the original table's columns, not the filtered subquery's —
            # combined with `.select_from(subquery)` that produced a
            # cartesian product between the two (SQLAlchemy warned; the
            # aggregate silently ran over the whole table, not the filtered
            # rows). Selecting the subquery's own `.c` column fixes this.
            duration_subquery = conversions.where(row.duration_ms.is_not(None)).subquery()
            avg_duration = session.scalar(select(func.avg(duration_subquery.c.duration_ms)))

            success_subquery = conversions.where(row.status == "success").subquery()
            total_files = (
                session.scalar(select(func.coalesce(func.sum(success_subquery.c.file_count), 0)))
                or 0
            )

        return OverviewMetrics(
            conversion_attempts=attempts,
            successful_conversions=successes,
            failed_conversions=failures,
            validation_rejections=rejections,
            rate_limit_rejections=rate_limited,
            success_rate=(successes / attempts) if attempts else 0.0,
            average_duration_ms=float(avg_duration) if avg_duration is not None else None,
            total_files_processed=int(total_files),
        )

    def get_daily_activity(self, since: datetime) -> list[DailyActivity]:
        from sqlalchemy import case, func, select

        from app.db.models import OperationsEventRow
        from app.db.session import session_scope

        row = OperationsEventRow
        day_col = func.date(row.created_at)
        with session_scope() as session:
            rows = session.execute(
                select(
                    day_col.label("day"),
                    func.count().label("attempts"),
                    func.sum(case((row.status == "success", 1), else_=0)).label("successes"),
                    func.sum(case((row.status != "success", 1), else_=0)).label("failures"),
                )
                .where(row.created_at >= since, row.event_type == "conversion")
                .group_by(day_col)
                .order_by(day_col)
            ).all()

        return [
            DailyActivity(
                day=r.day if isinstance(r.day, date) else datetime.fromisoformat(str(r.day)).date(),
                attempts=r.attempts,
                successes=r.successes,
                failures_or_rejections=r.failures,
            )
            for r in rows
        ]

    def get_tool_aggregation(self, since: datetime) -> list[ToolAggregation]:
        from sqlalchemy import case, func, select

        from app.db.models import OperationsEventRow
        from app.db.session import session_scope

        row = OperationsEventRow
        with session_scope() as session:
            rows = session.execute(
                select(
                    row.tool_slug,
                    func.count().label("attempts"),
                    func.sum(case((row.status == "success", 1), else_=0)).label("successes"),
                    func.sum(case((row.status == "failure", 1), else_=0)).label("failures"),
                    func.avg(row.duration_ms).label("avg_duration"),
                )
                .where(row.created_at >= since, row.event_type == "conversion", row.tool_slug.is_not(None))
                .group_by(row.tool_slug)
                .order_by(func.count().desc())
            ).all()

        results = []
        for r in rows:
            attempts = r.attempts or 0
            successes = r.successes or 0
            results.append(
                ToolAggregation(
                    tool_slug=r.tool_slug,
                    attempt_count=attempts,
                    success_count=successes,
                    failure_count=r.failures or 0,
                    success_rate=(successes / attempts) if attempts else 0.0,
                    average_duration_ms=float(r.avg_duration) if r.avg_duration is not None else None,
                )
            )
        return results

    def get_error_aggregation(self, since: datetime) -> list[tuple[str, int]]:
        from sqlalchemy import func, select

        from app.db.models import OperationsEventRow
        from app.db.session import session_scope

        row = OperationsEventRow
        with session_scope() as session:
            rows = session.execute(
                select(row.error_code, func.count())
                .where(row.created_at >= since, row.error_code.is_not(None))
                .group_by(row.error_code)
                .order_by(func.count().desc())
            ).all()
        return [(code, count) for code, count in rows]


_store: OperationsEventStore | None = None
_store_lock = threading.Lock()


def get_operations_event_store() -> OperationsEventStore:
    """Lazily builds the process-wide singleton, honoring
    `OPERATIONS_STORE_BACKEND`. "postgres" requires `DATABASE_URL` — see
    `app.db.session.get_engine`, which raises `DatabaseNotConfiguredError`
    rather than silently falling back to memory if it's missing. Mirrors
    `app.services.jobs.job_store`'s module-level-singleton pattern.
    """
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                settings = get_settings()
                if settings.operations_store_backend == "postgres":
                    _store = PostgresOperationsEventStore()
                else:
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
    settings: Settings | None = None,
) -> None:
    """Safe entry point every caller should use instead of the store
    directly — respects `OPERATIONS_EVENTS_ENABLED` and never lets a
    tracking failure propagate into the actual conversion request/response
    (logged instead, per the "instrumentation must not become a hard
    dependency for conversion success" requirement).

    Callers that already have a resolved `Settings` instance in scope
    (e.g. `run_conversion_job`, or a convert.py endpoint's own
    `Depends(get_settings)`) should pass it through here — otherwise this
    re-derives it via a fresh `get_settings()` call, which is correct for
    production (one process-wide cached settings object) but means a
    request-scoped settings override (as tests use) would silently not
    apply to this specific check.
    """
    settings = settings or get_settings()
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
