"""create operations_events and feedback tables

Revision ID: 0001
Revises:
Create Date: 2026-07-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operations_events",
        sa.Column("event_id", sa.String(length=32), primary_key=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("tool_slug", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("input_family", sa.String(length=32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("file_count >= 0", name="ck_operations_events_file_count_nonneg"),
    )
    op.create_index(
        "ix_operations_events_created_at", "operations_events", ["created_at"]
    )
    op.create_index("ix_operations_events_tool_slug", "operations_events", ["tool_slug"])
    op.create_index("ix_operations_events_status", "operations_events", ["status"])
    op.create_index("ix_operations_events_event_type", "operations_events", ["event_type"])
    op.create_index("ix_operations_events_error_code", "operations_events", ["error_code"])

    op.create_table(
        "feedback",
        sa.Column("feedback_id", sa.String(length=32), primary_key=True),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category in ('idea', 'suggestion', 'problem', 'other')",
            name="ck_feedback_category",
        ),
        sa.CheckConstraint(
            "status in ('new', 'reviewing', 'planned', 'completed', 'archived')",
            name="ck_feedback_status",
        ),
    )
    op.create_index("ix_feedback_status", "feedback", ["status"])
    op.create_index("ix_feedback_category", "feedback", ["category"])
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_created_at", table_name="feedback")
    op.drop_index("ix_feedback_category", table_name="feedback")
    op.drop_index("ix_feedback_status", table_name="feedback")
    op.drop_table("feedback")

    op.drop_index("ix_operations_events_error_code", table_name="operations_events")
    op.drop_index("ix_operations_events_event_type", table_name="operations_events")
    op.drop_index("ix_operations_events_status", table_name="operations_events")
    op.drop_index("ix_operations_events_tool_slug", table_name="operations_events")
    op.drop_index("ix_operations_events_created_at", table_name="operations_events")
    op.drop_table("operations_events")
