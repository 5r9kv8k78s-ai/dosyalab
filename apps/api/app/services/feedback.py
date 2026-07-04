"""Public "Bir fikrim var" (I have an idea) feedback — a minimal, privacy-safe
record of a user-submitted idea/suggestion/problem report. No IP address,
user agent, or fingerprinting of any kind; email is optional and used only
to display back to an admin, never as an identity or for sending mail.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

FeedbackCategory = Literal["idea", "suggestion", "problem", "other"]
FeedbackStatus = Literal["new", "reviewing", "planned", "completed", "archived"]

CATEGORIES: tuple[FeedbackCategory, ...] = ("idea", "suggestion", "problem", "other")
STATUSES: tuple[FeedbackStatus, ...] = ("new", "reviewing", "planned", "completed", "archived")

MESSAGE_MIN_LENGTH = 10
MESSAGE_MAX_LENGTH = 2000

# Deliberately simple — good enough to catch obvious typos without pulling
# in a full RFC 5322 parser for a field that's optional and never used to
# actually send mail.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class FeedbackValidationError(Exception):
    def __init__(self, message: str, error_code: str = "validation_failed"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


@dataclass(frozen=True)
class FeedbackRecord:
    feedback_id: str
    category: FeedbackCategory
    message: str
    email: str | None
    status: FeedbackStatus
    created_at: datetime
    updated_at: datetime


def validate_category(value: str) -> FeedbackCategory:
    if value not in CATEGORIES:
        raise FeedbackValidationError(
            f"category must be one of {', '.join(CATEGORIES)}.", error_code="invalid_category"
        )
    return value  # type: ignore[return-value]


def validate_message(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise FeedbackValidationError("message must not be empty.", error_code="invalid_message")
    if len(trimmed) < MESSAGE_MIN_LENGTH:
        raise FeedbackValidationError(
            f"message must be at least {MESSAGE_MIN_LENGTH} characters.",
            error_code="invalid_message",
        )
    if len(trimmed) > MESSAGE_MAX_LENGTH:
        raise FeedbackValidationError(
            f"message must be at most {MESSAGE_MAX_LENGTH} characters.",
            error_code="invalid_message",
        )
    return trimmed


def validate_email(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > 320 or not _EMAIL_RE.match(trimmed):
        raise FeedbackValidationError("email is not a valid address.", error_code="invalid_email")
    return trimmed


def validate_status(value: str) -> FeedbackStatus:
    if value not in STATUSES:
        raise FeedbackValidationError(
            f"status must be one of {', '.join(STATUSES)}.", error_code="invalid_status"
        )
    return value  # type: ignore[return-value]


class FeedbackStore(Protocol):
    def create(
        self, *, category: FeedbackCategory, message: str, email: str | None
    ) -> FeedbackRecord: ...

    def list(
        self, *, status: FeedbackStatus | None, category: FeedbackCategory | None
    ) -> list[FeedbackRecord]: ...

    def update_status(self, feedback_id: str, status: FeedbackStatus) -> FeedbackRecord | None: ...

    def summarize_by_status(self) -> dict[str, int]: ...


class PostgresFeedbackStore:
    """The only production implementation — feedback is meant to persist
    indefinitely for the Admin Panel, so there is no in-memory counterpart
    (unlike operations events, which have a bounded retention model)."""

    def __init__(self) -> None:
        from app.db.session import get_engine

        get_engine()

    def create(
        self, *, category: FeedbackCategory, message: str, email: str | None
    ) -> FeedbackRecord:
        from app.db.models import FeedbackRow
        from app.db.session import session_scope

        now = datetime.now(UTC)
        row = FeedbackRow(
            feedback_id=uuid.uuid4().hex,
            category=category,
            message=message,
            email=email,
            status="new",
            created_at=now,
            updated_at=now,
        )
        with session_scope() as session:
            session.add(row)
            session.flush()
            return _to_record(row)

    def list(
        self, *, status: FeedbackStatus | None, category: FeedbackCategory | None
    ) -> list[FeedbackRecord]:
        from sqlalchemy import select

        from app.db.models import FeedbackRow
        from app.db.session import session_scope

        query = select(FeedbackRow)
        if status is not None:
            query = query.where(FeedbackRow.status == status)
        if category is not None:
            query = query.where(FeedbackRow.category == category)
        query = query.order_by(FeedbackRow.created_at.desc())

        with session_scope() as session:
            rows = session.execute(query).scalars().all()
            return [_to_record(row) for row in rows]

    def update_status(self, feedback_id: str, status: FeedbackStatus) -> FeedbackRecord | None:
        from app.db.models import FeedbackRow
        from app.db.session import session_scope

        with session_scope() as session:
            row = session.get(FeedbackRow, feedback_id)
            if row is None:
                return None
            row.status = status
            row.updated_at = datetime.now(UTC)
            session.flush()
            return _to_record(row)

    def summarize_by_status(self) -> dict[str, int]:
        from sqlalchemy import func, select

        from app.db.models import FeedbackRow
        from app.db.session import session_scope

        with session_scope() as session:
            rows = session.execute(
                select(FeedbackRow.status, func.count()).group_by(FeedbackRow.status)
            ).all()
        return {status: count for status, count in rows}


def _to_record(row: "object") -> FeedbackRecord:
    return FeedbackRecord(
        feedback_id=row.feedback_id,  # type: ignore[attr-defined]
        category=row.category,  # type: ignore[attr-defined]
        message=row.message,  # type: ignore[attr-defined]
        email=row.email,  # type: ignore[attr-defined]
        status=row.status,  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
        updated_at=row.updated_at,  # type: ignore[attr-defined]
    )


_store: FeedbackStore | None = None


def get_feedback_store() -> FeedbackStore:
    global _store
    if _store is None:
        _store = PostgresFeedbackStore()
    return _store
