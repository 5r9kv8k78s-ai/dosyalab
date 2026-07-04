"""Feedback validation + the public endpoint, using an in-memory test
double for FeedbackStore (the correct boundary — the endpoint depends on
the `FeedbackStore` Protocol, not on Postgres directly) so these run
without any real database.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.feedback import _get_store
from app.core.config import Settings, get_settings
from app.main import app
from app.services.feedback import (
    FeedbackRecord,
    FeedbackValidationError,
    validate_category,
    validate_email,
    validate_message,
    validate_status,
)


class _FakeFeedbackStore:
    def __init__(self) -> None:
        self.created: list[FeedbackRecord] = []

    def create(self, *, category, message, email):
        now = datetime.now(UTC)
        record = FeedbackRecord(
            feedback_id=f"fake-{len(self.created)}",
            category=category,
            message=message,
            email=email,
            status="new",
            created_at=now,
            updated_at=now,
        )
        self.created.append(record)
        return record

    def list(self, *, status, category):
        return self.created

    def update_status(self, feedback_id, status):
        return None

    def summarize_by_status(self):
        return {}


@pytest.fixture
def fake_store():
    store = _FakeFeedbackStore()
    app.dependency_overrides[_get_store] = lambda: store
    yield store
    app.dependency_overrides.pop(_get_store, None)


@pytest.fixture
def feedback_test_settings(tmp_path) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        rate_limit_enabled=False,
        feedback_rate_limit_enabled=False,
    )


@pytest.fixture
def feedback_client(feedback_test_settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: feedback_test_settings
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)


# --- pure validation ---


def test_validate_message_rejects_too_short():
    with pytest.raises(FeedbackValidationError):
        validate_message("short")


def test_validate_message_rejects_whitespace_only():
    with pytest.raises(FeedbackValidationError):
        validate_message("             ")


def test_validate_message_accepts_valid():
    assert validate_message("  This is a valid idea.  ") == "This is a valid idea."


def test_validate_message_rejects_too_long():
    with pytest.raises(FeedbackValidationError):
        validate_message("x" * 2001)


def test_validate_email_optional():
    assert validate_email(None) is None
    assert validate_email("") is None


def test_validate_email_rejects_invalid():
    with pytest.raises(FeedbackValidationError):
        validate_email("not-an-email")


def test_validate_email_accepts_valid():
    assert validate_email("user@example.com") == "user@example.com"


def test_validate_category_rejects_unknown():
    with pytest.raises(FeedbackValidationError):
        validate_category("nonsense")


def test_validate_status_rejects_unknown():
    with pytest.raises(FeedbackValidationError):
        validate_status("nonsense")


def test_validate_status_accepts_known():
    assert validate_status("archived") == "archived"


# --- endpoint ---


def test_submit_feedback_success(feedback_client: TestClient, fake_store: _FakeFeedbackStore):
    response = feedback_client.post(
        "/api/v1/feedback",
        json={"category": "idea", "message": "DosyaLab için harika bir fikrim var.", "email": None},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    assert len(fake_store.created) == 1
    assert fake_store.created[0].email is None


def test_submit_feedback_rejects_short_message(
    feedback_client: TestClient, fake_store: _FakeFeedbackStore
):
    response = feedback_client.post(
        "/api/v1/feedback", json={"category": "idea", "message": "short"}
    )
    assert response.status_code == 400
    assert len(fake_store.created) == 0


def test_submit_feedback_rejects_invalid_email(
    feedback_client: TestClient, fake_store: _FakeFeedbackStore
):
    response = feedback_client.post(
        "/api/v1/feedback",
        json={"category": "idea", "message": "Bu geçerli bir mesajdır.", "email": "not-an-email"},
    )
    assert response.status_code == 400
    assert len(fake_store.created) == 0


def test_submit_feedback_rejects_invalid_category(
    feedback_client: TestClient, fake_store: _FakeFeedbackStore
):
    response = feedback_client.post(
        "/api/v1/feedback", json={"category": "nonsense", "message": "Bu geçerli bir mesajdır."}
    )
    assert response.status_code == 400


def test_feedback_rate_limit_returns_429(tmp_path, fake_store: _FakeFeedbackStore):
    import app.services.rate_limiter as rate_limiter_module

    rate_limiter_module._feedback_limiter = None
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        rate_limit_enabled=False,
        feedback_rate_limit_enabled=True,
        feedback_rate_limit_requests=1,
        feedback_rate_limit_window_seconds=600,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            first = client.post(
                "/api/v1/feedback",
                json={"category": "idea", "message": "Bu geçerli bir mesajdır."},
            )
            assert first.status_code == 201
            second = client.post(
                "/api/v1/feedback",
                json={"category": "idea", "message": "Bu ikinci mesajdır."},
            )
    finally:
        app.dependency_overrides.pop(get_settings, None)
        rate_limiter_module._feedback_limiter = None

    assert second.status_code == 429
    assert "Retry-After" in second.headers
