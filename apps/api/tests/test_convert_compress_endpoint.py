import io

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def _upload(client: TestClient, content: bytes):
    return client.post(
        "/api/v1/convert/compress-pdf",
        files={"file": ("sample.pdf", io.BytesIO(content), "application/pdf")},
    )


def test_compress_pdf_success_end_to_end(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    assert status_body["status"] == "completed"
    assert status_body["filename"] == "sample_compressed.pdf"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.content[:5] == b"%PDF-"

    followup = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}")
    assert followup.status_code == 404


def test_compress_rejects_non_pdf_extension(client_with_tmp_storage: TestClient) -> None:
    response = client_with_tmp_storage.post(
        "/api/v1/convert/compress-pdf",
        files={"file": ("notes.txt", io.BytesIO(b"just some text"), "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_compress_rejects_corrupted_pdf(
    client_with_tmp_storage: TestClient, corrupted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, corrupted_pdf_bytes)
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]


def test_compress_rejects_encrypted_pdf(
    client_with_tmp_storage: TestClient, encrypted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, encrypted_pdf_bytes)
    assert response.status_code == 400
    assert "Encrypted" in response.json()["detail"]


def test_compress_rejects_oversized_file(sample_pdf_bytes: bytes, tmp_path) -> None:
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
