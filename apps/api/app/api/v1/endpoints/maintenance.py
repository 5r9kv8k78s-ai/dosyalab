"""Public, unauthenticated Maintenance Mode status — the frontend's signal
to show the maintenance screen instead of the normal conversion UI (see
apps/web/components/maintenance/MaintenanceGate.tsx). Deliberately returns
only `enabled`/`message`: no admin, auth, or config detail ever belongs on
this route, since it's reachable without a token.

The admin-only update endpoint lives in admin.py instead, under the
existing `require_admin`-gated router.
"""

from fastapi import APIRouter, Depends

from app.schemas.maintenance import MaintenanceStatusResponse
from app.services.site_settings import SiteSettingsStore, get_site_settings_store

router = APIRouter(tags=["maintenance"])


@router.get("/maintenance/status", response_model=MaintenanceStatusResponse)
def get_maintenance_status(
    store: SiteSettingsStore = Depends(get_site_settings_store),
) -> MaintenanceStatusResponse:
    status = store.get_maintenance_status()
    return MaintenanceStatusResponse(enabled=status.enabled, message=status.message)
