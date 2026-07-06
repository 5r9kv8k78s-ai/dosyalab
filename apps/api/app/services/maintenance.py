"""The single choke point every conversion-submit route depends on (see
`app/api/v1/endpoints/convert.py`'s `_RATE_LIMITED` dependency list, applied
identically to every tool's POST route) — not a per-endpoint copy/paste
check. Backed by `app.services.site_settings`, which is Postgres-persisted,
so this is authoritative across restarts and replicas, unlike a process-
memory flag.
"""

import asyncio
import logging

from fastapi import Depends, HTTPException

from app.services.site_settings import SiteSettingsStore, get_site_settings_store

logger = logging.getLogger(__name__)

MAINTENANCE_ERROR_DETAIL = "DosyaLab is temporarily under maintenance. Please try again shortly."


async def enforce_not_in_maintenance(
    store: SiteSettingsStore = Depends(get_site_settings_store),
) -> None:
    # A blocking Postgres read, threaded exactly like every other blocking
    # DB call issued from async code in this codebase (see
    # app/services/conversion.py's `record_operations_event` usage) so it
    # can never block the event loop.
    status = await asyncio.to_thread(store.get_maintenance_status)
    if not status.enabled:
        return

    logger.info("maintenance.submit_rejected")
    raise HTTPException(status_code=503, detail=MAINTENANCE_ERROR_DETAIL)
