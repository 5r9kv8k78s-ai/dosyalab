"""Admin authentication/authorization and the protected admin API.

Supabase's JWKS/signature verification is mocked at the correct boundary —
`verify_supabase_access_token` — rather than weakening `require_admin`
itself; the allowlist check (`ADMIN_EMAILS`) and the 401/403 status logic
in `require_admin` run for real.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.admin import _get_event_store, _get_fb_store
from app.core.config import Settings, get_settings
from app.main import app
from app.services.admin_auth import require_admin
from app.services.feedback import FeedbackRecord
from app.services.operations_events import (
    DailyActivity,
    InMemoryOperationsEventStore,
    OverviewMetrics,
    ToolAggregation,
)


class _FakeEventStore:
    def get_overview(self, since):
        return OverviewMetrics(
            conversion_attempts=0,
            successful_conversions=0,
            failed_conversions=0,
            validation_rejections=0,
            rate_limit_rejections=0,
            success_rate=0.0,
            average_duration_ms=None,
            total_files_processed=0,
        )

    def get_daily_activity(self, since):
        return []

    def get_tool_aggregation(self, since):
        return []

    def get_error_aggregation(self, since):
        return []

    def record(self, **kwargs):
        pass

    def summarize_by_status(self):
        return {}

    def summarize_by_tool(self):
        return {}

    def summarize_by_error(self):
        return {}


class _FakeFeedbackStore:
    def __init__(self):
        now = datetime.now(UTC)
        self._items = [
            FeedbackRecord(
                feedback_id="f1",
                category="idea",
                message="Bir fikir",
                email=None,
                status="new",
                created_at=now,
                updated_at=now,
            )
        ]

    def create(self, *, category, message, email):
        raise NotImplementedError

    def list(self, *, status, category):
        return self._items

    def update_status(self, feedback_id, status):
        for item in self._items:
            if item.feedback_id == feedback_id:
                return FeedbackRecord(
                    feedback_id=item.feedback_id,
                    category=item.category,
                    message=item.message,
                    email=item.email,
                    status=status,
                    created_at=item.created_at,
                    updated_at=datetime.now(UTC),
                )
        return None

    def summarize_by_status(self):
        return {"new": 1}


@pytest.fixture
def admin_test_settings(tmp_path) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        rate_limit_enabled=False,
        admin_emails="admin@example.com",
        supabase_url="https://example.supabase.co",
    )


@pytest.fixture
def admin_client_no_auth_override(admin_test_settings):
    app.dependency_overrides[get_settings] = lambda: admin_test_settings
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def admin_client_authorized(admin_test_settings):
    from app.services.admin_auth import AdminIdentity

    app.dependency_overrides[get_settings] = lambda: admin_test_settings
    app.dependency_overrides[require_admin] = lambda: AdminIdentity(email="admin@example.com")
    app.dependency_overrides[_get_event_store] = lambda: _FakeEventStore()
    app.dependency_overrides[_get_fb_store] = lambda: _FakeFeedbackStore()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(_get_event_store, None)
        app.dependency_overrides.pop(_get_fb_store, None)


def test_missing_token_returns_401(admin_client_no_auth_override: TestClient):
    response = admin_client_no_auth_override.get("/api/v1/admin/overview")
    assert response.status_code == 401


def test_invalid_bearer_scheme_returns_401(admin_client_no_auth_override: TestClient):
    response = admin_client_no_auth_override.get(
        "/api/v1/admin/overview", headers={"Authorization": "Basic not-a-bearer-token"}
    )
    assert response.status_code == 401


def test_invalid_token_returns_401(admin_client_no_auth_override: TestClient, monkeypatch):
    from app.services import admin_auth

    def _raise(*args, **kwargs):
        raise admin_auth.AdminAuthError(401, "Invalid or expired authentication.")

    monkeypatch.setattr(admin_auth, "verify_supabase_access_token", _raise)
    response = admin_client_no_auth_override.get(
        "/api/v1/admin/overview", headers={"Authorization": "Bearer bad-token"}
    )
    assert response.status_code == 401


def test_authenticated_non_admin_returns_403(admin_client_no_auth_override: TestClient, monkeypatch):
    from app.services import admin_auth

    monkeypatch.setattr(
        admin_auth, "verify_supabase_access_token", lambda token, settings: "nobody@example.com"
    )
    response = admin_client_no_auth_override.get(
        "/api/v1/admin/overview", headers={"Authorization": "Bearer some-token"}
    )
    assert response.status_code == 403


def test_authenticated_admin_is_allowed(admin_client_no_auth_override: TestClient, monkeypatch):
    from app.services import admin_auth

    monkeypatch.setattr(
        admin_auth, "verify_supabase_access_token", lambda token, settings: "Admin@Example.com"
    )
    # email comparison is case-insensitive/normalized
    response = admin_client_no_auth_override.get(
        "/api/v1/admin/overview", headers={"Authorization": "Bearer some-token"}
    )
    assert response.status_code == 200


def test_overview_endpoint_zero_data(admin_client_authorized: TestClient):
    response = admin_client_authorized.get("/api/v1/admin/overview?range=7d")
    assert response.status_code == 200
    body = response.json()
    assert body["conversion_attempts"] == 0
    assert body["success_rate"] == 0.0


def test_overview_endpoint_rejects_bad_range(admin_client_authorized: TestClient):
    response = admin_client_authorized.get("/api/v1/admin/overview?range=nonsense")
    assert response.status_code == 400


def test_feedback_list_endpoint(admin_client_authorized: TestClient):
    response = admin_client_authorized.get("/api/v1/admin/feedback")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["feedback_id"] == "f1"


def test_feedback_status_update_endpoint(admin_client_authorized: TestClient):
    response = admin_client_authorized.patch(
        "/api/v1/admin/feedback/f1", json={"status": "reviewing"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "reviewing"


def test_feedback_status_update_rejects_invalid_status(admin_client_authorized: TestClient):
    response = admin_client_authorized.patch(
        "/api/v1/admin/feedback/f1", json={"status": "nonsense"}
    )
    assert response.status_code == 400


def test_feedback_status_update_missing_id_returns_404(admin_client_authorized: TestClient):
    response = admin_client_authorized.patch(
        "/api/v1/admin/feedback/does-not-exist", json={"status": "reviewing"}
    )
    assert response.status_code == 404


def test_admin_email_set_normalizes_case_and_whitespace():
    settings = Settings(admin_emails=" Admin@Example.com , second@example.com ")
    assert settings.admin_email_set == {"admin@example.com", "second@example.com"}
