import io

import fitz
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def _upload(client: TestClient, content: bytes, order: str):
    return client.post(
        "/api/v1/convert/reorder-pages",
        files={"file": ("sample.pdf", io.BytesIO(content), "application/pdf")},
        data={"order": order},
    )


def test_reorder_reverses_pages_success(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    original = fitz.open(stream=sample_pdf_bytes, filetype="pdf")
    page_count = original.page_count
    reversed_order = ",".join(str(p) for p in range(page_count, 0, -1))

    response = _upload(client_with_tmp_storage, sample_pdf_bytes, order=reversed_order)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    assert status_body["status"] == "completed"
    assert status_body["filename"] == "sample_reordered.pdf"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    doc = fitz.open(stream=download_response.content, filetype="pdf")
    assert doc.page_count == page_count
    # First page of the reordered doc should match the last page of the original.
    assert doc[0].get_text() == original[page_count - 1].get_text()


def test_reorder_rejects_partial_list(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, order="1,2,3")
    assert response.status_code == 400
    assert "permutation" in response.json()["detail"].lower()


def test_reorder_rejects_duplicate_pages(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, order="1,1,2,3,4,5")
    assert response.status_code == 400


def test_reorder_rejects_out_of_range_page(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, order="1,2,3,4,5,999")
    assert response.status_code == 400


def test_reorder_rejects_corrupted_pdf(
    client_with_tmp_storage: TestClient, corrupted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, corrupted_pdf_bytes, order="1")
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]


def test_reorder_rejects_encrypted_pdf(
    client_with_tmp_storage: TestClient, encrypted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, encrypted_pdf_bytes, order="1")
    assert response.status_code == 400
    assert "Encrypted" in response.json()["detail"]


def test_reorder_rejects_oversized_file(sample_pdf_bytes: bytes, tmp_path) -> None:
    tiny_limit_settings = Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        max_convert_upload_size_mb=0,
    )
    app.dependency_overrides[get_settings] = lambda: tiny_limit_settings
    try:
        with TestClient(app) as client:
            response = _upload(client, sample_pdf_bytes, order="1,2,3,4,5,6")
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 413
