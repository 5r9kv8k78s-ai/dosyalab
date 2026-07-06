"""Site Maintenance Mode: the central conversion-submit guard (see
app/services/maintenance.py), the admin update endpoint, the public status
endpoint, and the "everything except conversion submit keeps working"
guarantee. Mirrors tests/test_admin_auth_and_endpoints.py's fixture
conventions — Supabase JWT verification is mocked at
`verify_supabase_access_token`, never by weakening `require_admin` itself.
"""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.admin import _get_site_settings_store
from app.core.config import Settings, get_settings
from app.main import app
from app.services.admin_auth import AdminIdentity, require_admin
from app.services.jobs import job_store
from app.services.site_settings import MaintenanceStatus, get_site_settings_store


class _FakeSiteSettingsStore:
    def __init__(self, enabled: bool = False, message: str | None = "Bakımdayız.") -> None:
        self._status = MaintenanceStatus(enabled=enabled, message=message)

    def get_maintenance_status(self) -> MaintenanceStatus:
        return self._status

    def set_maintenance_status(self, *, enabled: bool, message: str | None) -> MaintenanceStatus:
        self._status = MaintenanceStatus(enabled=enabled, message=message)
        return self._status


@pytest.fixture
def maintenance_test_settings(tmp_path) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        rate_limit_enabled=False,
        admin_emails="admin@example.com",
        supabase_url="https://example.supabase.co",
    )


@pytest.fixture
def fake_site_settings_store() -> _FakeSiteSettingsStore:
    return _FakeSiteSettingsStore(enabled=False)


@pytest.fixture
def client_with_maintenance_store(maintenance_test_settings, fake_site_settings_store):
    """A plain (non-admin-authenticated) client with the maintenance guard's
    store swapped for the in-memory fake — used for conversion-submit and
    public-status tests, which don't need admin auth at all."""
    app.dependency_overrides[get_settings] = lambda: maintenance_test_settings
    app.dependency_overrides[get_site_settings_store] = lambda: fake_site_settings_store
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_site_settings_store, None)


@pytest.fixture
def admin_client_authorized(maintenance_test_settings, fake_site_settings_store):
    app.dependency_overrides[get_settings] = lambda: maintenance_test_settings
    app.dependency_overrides[require_admin] = lambda: AdminIdentity(email="admin@example.com")
    app.dependency_overrides[get_site_settings_store] = lambda: fake_site_settings_store
    app.dependency_overrides[_get_site_settings_store] = lambda: fake_site_settings_store
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(get_site_settings_store, None)
        app.dependency_overrides.pop(_get_site_settings_store, None)


@pytest.fixture
def admin_client_no_auth_override(maintenance_test_settings, fake_site_settings_store):
    app.dependency_overrides[get_settings] = lambda: maintenance_test_settings
    app.dependency_overrides[get_site_settings_store] = lambda: fake_site_settings_store
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_site_settings_store, None)


def _post_docx_to_pdf(client: TestClient, sample_docx_bytes: bytes):
    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return client.post(
        "/api/v1/convert/docx-to-pdf",
        files={"file": ("doc.docx", io.BytesIO(sample_docx_bytes), content_type)},
    )


def _post_pdf_to_docx(client: TestClient, sample_pdf_bytes: bytes):
    return client.post(
        "/api/v1/convert/pdf-to-docx",
        files=[("file", ("doc.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
    )


# ---------------------------------------------------------------------------
# Default state / persistence contract
# ---------------------------------------------------------------------------


def test_maintenance_default_disabled() -> None:
    store = _FakeSiteSettingsStore()
    assert store.get_maintenance_status().enabled is False


# ---------------------------------------------------------------------------
# Admin update endpoint — auth boundary
# ---------------------------------------------------------------------------


def test_unauthenticated_cannot_change_maintenance(
    admin_client_no_auth_override: TestClient,
) -> None:
    response = admin_client_no_auth_override.patch(
        "/api/v1/admin/maintenance", json={"enabled": True}
    )
    assert response.status_code == 401


def test_non_admin_cannot_change_maintenance(
    admin_client_no_auth_override: TestClient, monkeypatch
) -> None:
    from app.services import admin_auth

    monkeypatch.setattr(
        admin_auth, "verify_supabase_access_token", lambda token, settings: "nobody@example.com"
    )
    response = admin_client_no_auth_override.patch(
        "/api/v1/admin/maintenance",
        json={"enabled": True},
        headers={"Authorization": "Bearer some-token"},
    )
    assert response.status_code == 403


def test_admin_can_enable_maintenance(
    admin_client_authorized: TestClient, fake_site_settings_store: _FakeSiteSettingsStore
) -> None:
    response = admin_client_authorized.patch(
        "/api/v1/admin/maintenance", json={"enabled": True, "message": "Bakımdayız, az kaldı."}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["message"] == "Bakımdayız, az kaldı."
    assert fake_site_settings_store.get_maintenance_status().enabled is True


def test_admin_can_disable_maintenance(admin_client_authorized: TestClient) -> None:
    admin_client_authorized.patch("/api/v1/admin/maintenance", json={"enabled": True})
    response = admin_client_authorized.patch("/api/v1/admin/maintenance", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["enabled"] is False


# ---------------------------------------------------------------------------
# Public status endpoint
# ---------------------------------------------------------------------------


def test_public_maintenance_status_endpoint_works_without_auth(
    client_with_maintenance_store: TestClient,
) -> None:
    response = client_with_maintenance_store.get("/api/v1/maintenance/status")
    assert response.status_code == 200
    body = response.json()
    assert body == {"enabled": False, "message": "Bakımdayız."}


def test_public_maintenance_status_never_leaks_admin_fields(
    client_with_maintenance_store: TestClient,
) -> None:
    response = client_with_maintenance_store.get("/api/v1/maintenance/status")
    body = response.json()
    assert set(body.keys()) == {"enabled", "message"}


# ---------------------------------------------------------------------------
# Conversion-submit boundary — the central guard
# ---------------------------------------------------------------------------


def test_conversion_submit_succeeds_when_maintenance_disabled(
    client_with_maintenance_store: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _post_pdf_to_docx(client_with_maintenance_store, sample_pdf_bytes)
    assert response.status_code == 202


def test_conversion_submit_returns_503_when_maintenance_enabled(
    maintenance_test_settings, sample_pdf_bytes: bytes
) -> None:
    store = _FakeSiteSettingsStore(enabled=True)
    app.dependency_overrides[get_settings] = lambda: maintenance_test_settings
    app.dependency_overrides[get_site_settings_store] = lambda: store
    try:
        with TestClient(app) as client:
            response = _post_pdf_to_docx(client, sample_pdf_bytes)
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_site_settings_store, None)

    assert response.status_code == 503


def test_different_tools_blocked_by_same_central_guard(
    maintenance_test_settings, sample_pdf_bytes: bytes, sample_docx_bytes: bytes
) -> None:
    store = _FakeSiteSettingsStore(enabled=True)
    app.dependency_overrides[get_settings] = lambda: maintenance_test_settings
    app.dependency_overrides[get_site_settings_store] = lambda: store
    try:
        with TestClient(app) as client:
            pdf_to_docx_response = _post_pdf_to_docx(client, sample_pdf_bytes)
            docx_to_pdf_response = _post_docx_to_pdf(client, sample_docx_bytes)
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_site_settings_store, None)

    assert pdf_to_docx_response.status_code == 503
    assert docx_to_pdf_response.status_code == 503


def test_maintenance_disabled_again_restores_conversion_submit(
    maintenance_test_settings, sample_pdf_bytes: bytes
) -> None:
    store = _FakeSiteSettingsStore(enabled=True)
    app.dependency_overrides[get_settings] = lambda: maintenance_test_settings
    app.dependency_overrides[get_site_settings_store] = lambda: store
    try:
        with TestClient(app) as client:
            blocked = _post_pdf_to_docx(client, sample_pdf_bytes)
            store.set_maintenance_status(enabled=False, message=None)
            allowed = _post_pdf_to_docx(client, sample_pdf_bytes)
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_site_settings_store, None)

    assert blocked.status_code == 503
    assert allowed.status_code == 202


# ---------------------------------------------------------------------------
# Everything else keeps working during maintenance
# ---------------------------------------------------------------------------


def test_job_status_endpoint_works_during_maintenance(
    client_with_maintenance_store: TestClient,
    fake_site_settings_store: _FakeSiteSettingsStore,
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.pdf"
    source_path.write_bytes(b"stub pdf content")
    job = job_store.create(
        module_slug="pdf-to-docx", source_path=source_path, download_filename="source.docx"
    )
    fake_site_settings_store.set_maintenance_status(enabled=True, message=None)

    response = client_with_maintenance_store.get(f"/api/v1/convert/jobs/{job.id}")
    assert response.status_code == 200


def test_download_endpoint_works_during_maintenance(
    client_with_maintenance_store: TestClient,
    fake_site_settings_store: _FakeSiteSettingsStore,
    tmp_path: Path,
) -> None:
    from app.services.jobs import JobStatus

    output_path = tmp_path / "result.docx"
    output_path.write_bytes(b"fake docx bytes")
    job = job_store.create(
        module_slug="pdf-to-docx", source_path=tmp_path / "src.pdf", download_filename="result.docx"
    )
    job_store.update(job.id, status=JobStatus.COMPLETED, output_path=output_path, progress=100)
    fake_site_settings_store.set_maintenance_status(enabled=True, message=None)

    response = client_with_maintenance_store.get(f"/api/v1/convert/jobs/{job.id}/download")
    assert response.status_code == 200


def test_admin_endpoints_work_during_maintenance(admin_client_authorized: TestClient) -> None:
    admin_client_authorized.patch("/api/v1/admin/maintenance", json={"enabled": True})
    response = admin_client_authorized.get("/api/v1/admin/overview?range=7d")
    assert response.status_code == 200


def test_maintenance_status_endpoint_works_during_maintenance(
    client_with_maintenance_store: TestClient, fake_site_settings_store: _FakeSiteSettingsStore
) -> None:
    fake_site_settings_store.set_maintenance_status(enabled=True, message="Bakımdayız.")
    response = client_with_maintenance_store.get("/api/v1/maintenance/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_health_endpoint_works_during_maintenance(
    client_with_maintenance_store: TestClient, fake_site_settings_store: _FakeSiteSettingsStore
) -> None:
    fake_site_settings_store.set_maintenance_status(enabled=True, message=None)
    response = client_with_maintenance_store.get("/api/v1/health")
    assert response.status_code == 200
