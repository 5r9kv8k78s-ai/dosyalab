"""Site-wide configuration — currently just Maintenance Mode. Backed by the
single-row `site_settings` table (see app/db/models.py, migrations/versions/
0002_site_settings.py) so state survives a Render redeploy/restart, unlike
`app.services.rate_limiter`'s process-local counters.

Postgres-backed only, like `app.services.feedback` — there is no in-memory
fallback, by design: maintenance state that silently isn't persistent is
worse than a startup error (see app.db.session.DatabaseNotConfiguredError).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

_SETTINGS_ROW_ID = 1

# Used only if the singleton row is somehow missing (e.g. `site_settings`
# exists but the migration's seed row was never applied) — the safe default
# is "not in maintenance", never a silent maintenance lockout.
DEFAULT_MAINTENANCE_MESSAGE = (
    "Size daha iyi hizmet verebilmek için kısa bir bakım çalışması yapıyoruz. "
    "Birazdan tekrar buradayız."
)


@dataclass(frozen=True)
class MaintenanceStatus:
    enabled: bool
    message: str | None


class SiteSettingsStore(Protocol):
    def get_maintenance_status(self) -> MaintenanceStatus: ...

    def set_maintenance_status(
        self, *, enabled: bool, message: str | None
    ) -> MaintenanceStatus: ...


class PostgresSiteSettingsStore:
    """The only production implementation — see module docstring for why
    there is no in-memory counterpart."""

    def __init__(self) -> None:
        from app.db.session import get_engine

        get_engine()

    def get_maintenance_status(self) -> MaintenanceStatus:
        from app.db.models import SiteSettingsRow
        from app.db.session import session_scope

        with session_scope() as session:
            row = session.get(SiteSettingsRow, _SETTINGS_ROW_ID)
            if row is None:
                return MaintenanceStatus(enabled=False, message=DEFAULT_MAINTENANCE_MESSAGE)
            return MaintenanceStatus(
                enabled=row.maintenance_enabled, message=row.maintenance_message
            )

    def set_maintenance_status(self, *, enabled: bool, message: str | None) -> MaintenanceStatus:
        from app.db.models import SiteSettingsRow
        from app.db.session import session_scope

        with session_scope() as session:
            row = session.get(SiteSettingsRow, _SETTINGS_ROW_ID)
            now = datetime.now(UTC)
            if row is None:
                row = SiteSettingsRow(
                    id=_SETTINGS_ROW_ID,
                    maintenance_enabled=enabled,
                    maintenance_message=message,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.maintenance_enabled = enabled
                row.maintenance_message = message
                row.updated_at = now
            session.flush()
            return MaintenanceStatus(
                enabled=row.maintenance_enabled, message=row.maintenance_message
            )


_store: SiteSettingsStore | None = None


def get_site_settings_store() -> SiteSettingsStore:
    global _store
    if _store is None:
        _store = PostgresSiteSettingsStore()
    return _store
