import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.admin import (
    DailyActivityItem,
    ErrorAggregationItem,
    ErrorsResponse,
    FeedbackAdminItem,
    FeedbackListResponse,
    OperationsHistoryClearResponse,
    OverviewChartResponse,
    OverviewResponse,
    ToolAggregationItem,
    ToolsResponse,
)
from app.schemas.feedback import FeedbackStatusUpdateRequest
from app.schemas.maintenance import MaintenanceStatusResponse, MaintenanceUpdateRequest
from app.services.admin_auth import require_admin
from app.services.feedback import (
    STATUSES as FEEDBACK_STATUSES,
    FeedbackStore,
    FeedbackValidationError,
    get_feedback_store,
    validate_status,
)
from app.services.operations_events import OperationsEventStore, get_operations_event_store
from app.services.site_settings import SiteSettingsStore, get_site_settings_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

_RANGE_TO_TIMEDELTA = {
    "today": None,  # handled specially — start of today, not "24 hours ago"
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def _resolve_since(range_key: str) -> datetime:
    if range_key not in _RANGE_TO_TIMEDELTA:
        raise HTTPException(status_code=400, detail="range must be one of: today, 7d, 30d.")
    now = datetime.now(UTC)
    if range_key == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    return now - _RANGE_TO_TIMEDELTA[range_key]


def _get_event_store() -> OperationsEventStore:
    return get_operations_event_store()


def _get_fb_store() -> FeedbackStore:
    return get_feedback_store()


def _get_site_settings_store() -> SiteSettingsStore:
    return get_site_settings_store()


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    range: str = Query("7d"),
    store: OperationsEventStore = Depends(_get_event_store),
) -> OverviewResponse:
    since = _resolve_since(range)
    metrics = store.get_overview(since)
    return OverviewResponse(range=range, **metrics.__dict__)


@router.get("/overview/chart", response_model=OverviewChartResponse)
def get_overview_chart(
    range: str = Query("7d"),
    store: OperationsEventStore = Depends(_get_event_store),
) -> OverviewChartResponse:
    since = _resolve_since(range)
    days = store.get_daily_activity(since)
    return OverviewChartResponse(
        range=range,
        days=[DailyActivityItem(**day.__dict__) for day in days],
    )


@router.get("/tools", response_model=ToolsResponse)
def get_tools(
    range: str = Query("7d"),
    store: OperationsEventStore = Depends(_get_event_store),
) -> ToolsResponse:
    since = _resolve_since(range)
    tools = store.get_tool_aggregation(since)
    return ToolsResponse(range=range, tools=[ToolAggregationItem(**t.__dict__) for t in tools])


@router.get("/errors", response_model=ErrorsResponse)
def get_errors(
    range: str = Query("7d"),
    store: OperationsEventStore = Depends(_get_event_store),
) -> ErrorsResponse:
    since = _resolve_since(range)
    errors = store.get_error_aggregation(since)
    return ErrorsResponse(
        range=range,
        errors=[ErrorAggregationItem(error_code=code, count=count) for code, count in errors],
    )


@router.get("/feedback", response_model=FeedbackListResponse)
def list_feedback(
    status: str | None = Query(None),
    category: str | None = Query(None),
    store: FeedbackStore = Depends(_get_fb_store),
) -> FeedbackListResponse:
    if status is not None and status not in FEEDBACK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status filter.")

    records = store.list(status=status, category=category)  # type: ignore[arg-type]
    counts = store.summarize_by_status()
    return FeedbackListResponse(
        items=[FeedbackAdminItem(**record.__dict__) for record in records],
        counts_by_status=counts,
    )


@router.patch("/feedback/{feedback_id}", response_model=FeedbackAdminItem)
def update_feedback_status(
    feedback_id: str,
    payload: FeedbackStatusUpdateRequest,
    store: FeedbackStore = Depends(_get_fb_store),
) -> FeedbackAdminItem:
    try:
        status_value = validate_status(payload.status)
    except FeedbackValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    updated = store.update_status(feedback_id, status_value)
    if updated is None:
        raise HTTPException(status_code=404, detail="Feedback not found.")
    return FeedbackAdminItem(**updated.__dict__)


@router.delete("/operations-history", response_model=OperationsHistoryClearResponse)
def clear_operations_history(
    store: OperationsEventStore = Depends(_get_event_store),
) -> OperationsHistoryClearResponse:
    """Admin Panel's "Geçmişi Temizle" action — deletes every operations
    event (the data behind Overview/Tools/Errors), and nothing else. Never
    touches the conversion job store, feedback, uploaded/output files, auth,
    or settings data; this store has no handle on any of them."""
    deleted_count = store.clear_all()
    logger.warning("admin.operations_history_cleared", extra={"deleted_count": deleted_count})
    return OperationsHistoryClearResponse(deleted_count=deleted_count)


@router.get("/maintenance", response_model=MaintenanceStatusResponse)
def get_admin_maintenance_status(
    store: SiteSettingsStore = Depends(_get_site_settings_store),
) -> MaintenanceStatusResponse:
    status = store.get_maintenance_status()
    return MaintenanceStatusResponse(enabled=status.enabled, message=status.message)


@router.patch("/maintenance", response_model=MaintenanceStatusResponse)
def update_maintenance_status(
    payload: MaintenanceUpdateRequest,
    store: SiteSettingsStore = Depends(_get_site_settings_store),
) -> MaintenanceStatusResponse:
    updated = store.set_maintenance_status(enabled=payload.enabled, message=payload.message)
    logger.warning(
        "admin.maintenance_status_changed", extra={"maintenance_enabled": updated.enabled}
    )
    return MaintenanceStatusResponse(enabled=updated.enabled, message=updated.message)
