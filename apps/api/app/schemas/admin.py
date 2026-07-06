from datetime import date, datetime

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    range: str
    conversion_attempts: int
    successful_conversions: int
    failed_conversions: int
    validation_rejections: int
    rate_limit_rejections: int
    success_rate: float
    average_duration_ms: float | None
    total_files_processed: int


class DailyActivityItem(BaseModel):
    day: date
    attempts: int
    successes: int
    failures_or_rejections: int


class OverviewChartResponse(BaseModel):
    range: str
    days: list[DailyActivityItem]


class ToolAggregationItem(BaseModel):
    tool_slug: str
    attempt_count: int
    success_count: int
    failure_count: int
    success_rate: float
    average_duration_ms: float | None


class ToolsResponse(BaseModel):
    range: str
    tools: list[ToolAggregationItem]


class ErrorAggregationItem(BaseModel):
    error_code: str
    count: int


class ErrorsResponse(BaseModel):
    range: str
    errors: list[ErrorAggregationItem]


class FeedbackAdminItem(BaseModel):
    feedback_id: str
    category: str
    message: str
    email: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class FeedbackListResponse(BaseModel):
    items: list[FeedbackAdminItem]
    counts_by_status: dict[str, int]


class OperationsHistoryClearResponse(BaseModel):
    deleted_count: int
