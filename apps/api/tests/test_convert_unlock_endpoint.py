import io
import time

import fitz
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def _upload(client: TestClient, content: bytes, password: str):
    return client.post(
        "/api/v1/convert/unlock-pdf",
        files={"file": ("encrypted.pdf", io.BytesIO(content), "application/pdf")},
        data={"password": password},
    )


def _poll_until_settled(client: TestClient, job_id: str, timeout_s: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        body = client.get(f"/api/v1/convert/jobs/{job_id}").json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(0.05)
    raise AssertionError("job did not settle in time")


def test_unlock_success_end_to_end(
    client_with_tmp_storage: TestClient, encrypted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, encrypted_pdf_bytes, password="user-secret")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = _poll_until_settled(client_with_tmp_storage, job_id)
    assert status_body["status"] == "completed"
    assert status_body["filename"] == "encrypted_unlocked.pdf"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    doc = fitz.open(stream=download_response.content, filetype="pdf")
    assert not doc.needs_pass


def test_unlock_with_wrong_password_fails_as_job_not_validation_error(
    client_with_tmp_storage: TestClient, encrypted_pdf_bytes: bytes
) -> None:
    # Encryption is only detectable by actually trying to authenticate, so a
    # wrong password surfaces as a failed job, not a 400 at submission time.
    response = _upload(client_with_tmp_storage, encrypted_pdf_bytes, password="totally-wrong")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = _poll_until_settled(client_with_tmp_storage, job_id)
    assert status_body["status"] == "failed"


def test_unlock_accepts_unencrypted_pdf_as_no_op(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    # PdfEngine.unlock_pdf only authenticates if the doc is actually
    # encrypted, so a plain PDF should pass through unchanged rather than
    # erroring.
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, password="unused")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = _poll_until_settled(client_with_tmp_storage, job_id)
    assert status_body["status"] == "completed"


def test_unlock_rejects_empty_password(
    client_with_tmp_storage: TestClient, encrypted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, encrypted_pdf_bytes, password="")
    assert response.status_code == 400


def test_unlock_rejects_corrupted_pdf(
    client_with_tmp_storage: TestClient, corrupted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, corrupted_pdf_bytes, password="whatever")
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]


def test_unlock_rejects_oversized_file(encrypted_pdf_bytes: bytes, tmp_path) -> None:
    tiny_limit_settings = Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        max_convert_upload_size_mb=0,
    )
    app.dependency_overrides[get_settings] = lambda: tiny_limit_settings
    try:
        with TestClient(app) as client:
            response = _upload(client, encrypted_pdf_bytes, password="user-secret")
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 413
