import io
import time
import zipfile
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def image_free_pdf_bytes(sample_pdf_path: Path, tmp_path: Path) -> bytes:
    # Page 1 of sample.pdf has no embedded images (verified empirically) —
    # extracting just that page gives a real, valid PDF with zero images,
    # to exercise the "nothing to extract" path without any synthetic content.
    doc = fitz.open(sample_pdf_path)
    doc.select([0])
    output = tmp_path / "image_free.pdf"
    doc.save(output)
    doc.close()
    return output.read_bytes()


def _upload(client: TestClient, content: bytes):
    return client.post(
        "/api/v1/convert/extract-images",
        files={"file": ("sample.pdf", io.BytesIO(content), "application/pdf")},
    )


def _poll_until_settled(client: TestClient, job_id: str, timeout_s: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        body = client.get(f"/api/v1/convert/jobs/{job_id}").json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(0.05)
    raise AssertionError("job did not settle in time")


def test_extract_images_success_end_to_end(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = _poll_until_settled(client_with_tmp_storage, job_id)
    assert status_body["status"] == "completed"
    assert status_body["filename"] == "sample_images.zip"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/zip"

    archive = zipfile.ZipFile(io.BytesIO(download_response.content))
    # sample.pdf has 5 embedded images (verified empirically).
    assert len(archive.namelist()) == 5


def test_extract_images_fails_job_when_no_images_present(
    client_with_tmp_storage: TestClient, image_free_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, image_free_pdf_bytes)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = _poll_until_settled(client_with_tmp_storage, job_id)
    assert status_body["status"] == "failed"


def test_extract_images_rejects_non_pdf_extension(client_with_tmp_storage: TestClient) -> None:
    response = client_with_tmp_storage.post(
        "/api/v1/convert/extract-images",
        files={"file": ("notes.txt", io.BytesIO(b"just some text"), "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_extract_images_rejects_corrupted_pdf(
    client_with_tmp_storage: TestClient, corrupted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, corrupted_pdf_bytes)
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]


def test_extract_images_rejects_encrypted_pdf(
    client_with_tmp_storage: TestClient, encrypted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, encrypted_pdf_bytes)
    assert response.status_code == 400
    assert "Encrypted" in response.json()["detail"]


def test_extract_images_rejects_oversized_file(sample_pdf_bytes: bytes, tmp_path) -> None:
    tiny_limit_settings = Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        max_convert_upload_size_mb=0,
    )
    app.dependency_overrides[get_settings] = lambda: tiny_limit_settings
    try:
        with TestClient(app) as client:
            response = _upload(client, sample_pdf_bytes)
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 413
