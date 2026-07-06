"""Admin Panel "Geçmişi Temizle" (clear operations history) endpoint —
auth boundary and the "scoped to operations_events only" guarantee.
Mirrors tests/test_admin_auth_and_endpoints.py's fixture conventions.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.admin import _get_event_store
from app.core.config import Settings, get_settings
from app.main import app
from app.services.admin_auth import AdminIdentity, require_admin
from app.services.jobs import JobStatus, job_store


class _FakeEventStore:
    def __init__(self) -> None:
        self.cleared = False

    def clear_all(self) -> int:
        self.cleared = True
        return 7


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
def fake_event_store() -> _FakeEventStore:
    return _FakeEventStore()


@pytest.fixture
def admin_client_authorized(admin_test_settings, fake_event_store):
    app.dependency_overrides[get_settings] = lambda: admin_test_settings
    app.dependency_overrides[require_admin] = lambda: AdminIdentity(email="admin@example.com")
    app.dependency_overrides[_get_event_store] = lambda: fake_event_store
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(_get_event_store, None)


def test_unauthenticated_cannot_clear_history(admin_client_no_auth_override: TestClient) -> None:
    response = admin_client_no_auth_override.delete("/api/v1/admin/operations-history")
    assert response.status_code == 401


def test_authenticated_non_admin_cannot_clear_history(
    admin_client_no_auth_override: TestClient, monkeypatch
) -> None:
    from app.services import admin_auth

    monkeypatch.setattr(
        admin_auth, "verify_supabase_access_token", lambda token, settings: "nobody@example.com"
    )
    response = admin_client_no_auth_override.delete(
        "/api/v1/admin/operations-history", headers={"Authorization": "Bearer some-token"}
    )
    assert response.status_code == 403


def test_admin_can_clear_history(
    admin_client_authorized: TestClient, fake_event_store: _FakeEventStore
) -> None:
    response = admin_client_authorized.delete("/api/v1/admin/operations-history")
    assert response.status_code == 200
    assert response.json() == {"deleted_count": 7}
    assert fake_event_store.cleared is True


def test_clear_history_does_not_touch_active_conversion_job(
    admin_client_authorized: TestClient, tmp_path: Path
) -> None:
    source_path = tmp_path / "source.pdf"
    source_path.write_bytes(b"stub pdf content")
    job = job_store.create(
        module_slug="pdf-to-docx", source_path=source_path, download_filename="source.docx"
    )

    response = admin_client_authorized.delete("/api/v1/admin/operations-history")

    assert response.status_code == 200
    still_there = job_store.get(job.id)
    assert still_there is not None
    assert still_there.status == JobStatus.PENDING
