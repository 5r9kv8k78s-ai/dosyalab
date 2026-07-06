"""SQLAlchemy models for DosyaLab's persistent operational data.

Both tables intentionally hold only the fields already approved for their
respective in-memory models (see app/services/operations_events.py and
the feedback schema in app/services/feedback.py) — there is no filename,
file content, document text, user identity, raw IP, or user-agent column
anywhere here, by construction.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OperationsEventRow(Base):
    """Persistent counterpart of `app.services.operations_events.OperationsEvent`.

    Indexes are chosen from the actual Admin Panel queries this table
    serves (see app/services/admin_metrics.py): `created_at` for every
    date-range query, `tool_slug` for the Tools screen, `status` for the
    Overview's success/failure/rejection breakdown, `event_type` to
    separate conversion attempts from rate-limit rejections, and
    `error_code` for the Errors screen. No other column is indexed.
    """

    __tablename__ = "operations_events"

    event_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    tool_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_family: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("file_count >= 0", name="ck_operations_events_file_count_nonneg"),
        Index("ix_operations_events_created_at", "created_at"),
        Index("ix_operations_events_tool_slug", "tool_slug"),
        Index("ix_operations_events_status", "status"),
        Index("ix_operations_events_event_type", "event_type"),
        Index("ix_operations_events_error_code", "error_code"),
    )


_FEEDBACK_CATEGORIES = ("idea", "suggestion", "problem", "other")
_FEEDBACK_STATUSES = ("new", "reviewing", "planned", "completed", "archived")


class FeedbackRow(Base):
    """"Bir fikrim var" submissions. `message` is always rendered as plain
    text by the frontend (never `dangerouslySetInnerHTML`) — see
    components/feedback/FeedbackListItem.tsx in the Admin Panel."""

    __tablename__ = "feedback"

    feedback_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            f"category in ({', '.join(repr(c) for c in _FEEDBACK_CATEGORIES)})",
            name="ck_feedback_category",
        ),
        CheckConstraint(
            f"status in ({', '.join(repr(s) for s in _FEEDBACK_STATUSES)})",
            name="ck_feedback_status",
        ),
        Index("ix_feedback_status", "status"),
        Index("ix_feedback_category", "category"),
        Index("ix_feedback_created_at", "created_at"),
    )


class SiteSettingsRow(Base):
    """Single-row site-wide configuration — currently just maintenance mode
    (see app/services/site_settings.py). A dedicated singleton row (fixed
    `id=1`, enforced by the check constraint below) rather than a generic
    key/value table: there is exactly one setting group today, and this
    stays the narrowest schema that satisfies it without speculating about
    future settings that don't exist yet.

    Deliberately Postgres-backed only, like `FeedbackRow` — maintenance
    state must survive a Render redeploy/restart, which process memory
    cannot guarantee (see app/services/rate_limiter.py's docstring for what
    goes wrong when state is only ever in-process).
    """

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    maintenance_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    maintenance_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (CheckConstraint("id = 1", name="ck_site_settings_singleton"),)
