"""create site_settings table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_MAINTENANCE_MESSAGE = (
    "Size daha iyi hizmet verebilmek için kısa bir bakım çalışması yapıyoruz. "
    "Birazdan tekrar buradayız."
)


def upgrade() -> None:
    op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("maintenance_enabled", sa.Boolean(), nullable=False),
        sa.Column("maintenance_message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_site_settings_singleton"),
    )

    # Seeds the single settings row so a fresh read (before any admin ever
    # touches Maintenance Mode) finds maintenance disabled rather than an
    # absent row — additive only, no existing table's data is touched.
    # `sa.func.now()` (not raw `now()` SQL) so this also runs against the
    # SQLite engine this migration is verified against locally, not only
    # production Postgres.
    site_settings = sa.table(
        "site_settings",
        sa.column("id", sa.Integer()),
        sa.column("maintenance_enabled", sa.Boolean()),
        sa.column("maintenance_message", sa.Text()),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        site_settings.insert().values(
            id=1,
            maintenance_enabled=False,
            maintenance_message=_DEFAULT_MAINTENANCE_MESSAGE,
            updated_at=sa.func.now(),
        )
    )


def downgrade() -> None:
    op.drop_table("site_settings")
