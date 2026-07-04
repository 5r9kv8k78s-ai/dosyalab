import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.feedback import FeedbackCreated, FeedbackCreateRequest
from app.services.feedback import (
    FeedbackStore,
    FeedbackValidationError,
    get_feedback_store,
    validate_category,
    validate_email,
    validate_message,
)
from app.services.rate_limiter import enforce_feedback_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _get_store() -> FeedbackStore:
    return get_feedback_store()


@router.post(
    "",
    response_model=FeedbackCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_feedback_rate_limit)],
)
def submit_feedback(
    payload: FeedbackCreateRequest,
    store: FeedbackStore = Depends(_get_store),
) -> FeedbackCreated:
    try:
        category = validate_category(payload.category)
        message = validate_message(payload.message)
        email = validate_email(payload.email)
    except FeedbackValidationError as exc:
        logger.warning("feedback.validation_failed", extra={"reason": exc.error_code})
        raise HTTPException(status_code=400, detail=exc.message) from exc

    record = store.create(category=category, message=message, email=email)
    logger.info("feedback.created", extra={"feedback_id": record.feedback_id})
    return FeedbackCreated(feedback_id=record.feedback_id, status=record.status)
