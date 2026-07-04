"""Endpoint-level rate-limit tests through the real FastAPI app.

`app.services.rate_limiter` builds its conversion limiter as a module-level
singleton the first time it's needed (see `_get_conversion_limiter`), so
every test here resets that singleton first — otherwise a limiter built
with one test's settings would leak into the next.
"""

import io

from fastapi.testclient import TestClient

import app.services.rate_limiter as rate_limiter_module
from app.core.config import Settings, get_settings
from app.main import app


def _tiny_limit_settings(tmp_path, max_requests: int) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        rate_limit_enabled=True,
        rate_limit_requests=max_requests,
        rate_limit_window_seconds=60,
    )


def _post_pdf_to_docx(client: TestClient, sample_pdf_bytes: bytes):
    return client.post(
        "/api/v1/convert/pdf-to-docx",
        files=[("file", ("doc.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
    )


def test_requests_below_threshold_are_not_rate_limited(tmp_path, sample_pdf_bytes: bytes) -> None:
    rate_limiter_module._conversion_limiter = None
    settings = _tiny_limit_settings(tmp_path, max_requests=5)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            for _ in range(3):
                response = _post_pdf_to_docx(client, sample_pdf_bytes)
                assert response.status_code == 202
    finally:
        app.dependency_overrides.pop(get_settings, None)
        rate_limiter_module._conversion_limiter = None


def test_returns_429_with_retry_after_above_threshold(tmp_path, sample_pdf_bytes: bytes) -> None:
    rate_limiter_module._conversion_limiter = None
    settings = _tiny_limit_settings(tmp_path, max_requests=2)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            assert _post_pdf_to_docx(client, sample_pdf_bytes).status_code == 202
            assert _post_pdf_to_docx(client, sample_pdf_bytes).status_code == 202
            blocked = _post_pdf_to_docx(client, sample_pdf_bytes)
    finally:
        app.dependency_overrides.pop(get_settings, None)
        rate_limiter_module._conversion_limiter = None

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert int(blocked.headers["Retry-After"]) > 0
    # The 429 body must stay a calm, generic message — no limiter internals.
    assert "too many requests" in blocked.json()["detail"].lower()


def test_rate_limit_disabled_setting_bypasses_the_limiter(
    tmp_path, sample_pdf_bytes: bytes
) -> None:
    rate_limiter_module._conversion_limiter = None
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        rate_limit_enabled=False,
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            for _ in range(3):
                response = _post_pdf_to_docx(client, sample_pdf_bytes)
                assert response.status_code == 202
    finally:
        app.dependency_overrides.pop(get_settings, None)
        rate_limiter_module._conversion_limiter = None
