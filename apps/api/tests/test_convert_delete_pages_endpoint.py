import io

import fitz
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def _upload(client: TestClient, content: bytes, pages: str = "1"):
    return client.post(
        "/api/v1/convert/delete-pages",
        files={"file": ("sample.pdf", io.BytesIO(content), "application/pdf")},
        data={"pages": pages},
    )


def test_delete_single_page_success(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, pages="1")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    assert status_body["status"] == "completed"
    assert status_body["filename"] == "sample_edited.pdf"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    doc = fitz.open(stream=download_response.content, filetype="pdf")
    assert doc.page_count == 5


def test_delete_multiple_pages_success(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, pages="1,3,5")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    download_response = client_with_tmp_storage.get(status_body["download_url"])
    doc = fitz.open(stream=download_response.content, filetype="pdf")
    assert doc.page_count == 3


def test_delete_rejects_all_pages(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, pages="1,2,3,4,5,6")
    assert response.status_code == 400
    assert "all pages" in response.json()["detail"].lower()


def test_delete_rejects_out_of_range_page(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, pages="999")
    assert response.status_code == 400
    assert "out of range" in response.json()["detail"]


def test_delete_rejects_empty_pages(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, pages="")
    assert response.status_code == 400


def test_delete_rejects_corrupted_pdf(
    client_with_tmp_storage: TestClient, corrupted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, corrupted_pdf_bytes)
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]


def test_delete_rejects_encrypted_pdf(
    client_with_tmp_storage: TestClient, encrypted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, encrypted_pdf_bytes)
    assert response.status_code == 400
    assert "Encrypted" in response.json()["detail"]


def test_delete_rejects_oversized_file(sample_pdf_bytes: bytes, tmp_path) -> None:
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
