from datetime import datetime

from pydantic import BaseModel


class FeedbackCreateRequest(BaseModel):
    category: str
    message: str
    email: str | None = None


class FeedbackCreated(BaseModel):
    feedback_id: str
    status: str


class FeedbackAdminItem(BaseModel):
    feedback_id: str
    category: str
    message: str
    email: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class FeedbackStatusUpdateRequest(BaseModel):
    status: str
