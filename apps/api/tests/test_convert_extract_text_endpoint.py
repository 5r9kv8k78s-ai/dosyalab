import io

import fitz
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def _upload(client: TestClient, content: bytes, pages: str | None = None):
    data = {} if pages is None else {"pages": pages}
    return client.post(
        "/api/v1/convert/extract-text",
        files={"file": ("sample.pdf", io.BytesIO(content), "application/pdf")},
        data=data,
    )


def test_extract_text_all_pages_success(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    assert status_body["status"] == "completed"
    assert status_body["filename"] == "sample.txt"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("text/plain")
    full_text = download_response.content.decode("utf-8")
    assert len(full_text) > 0


def test_extract_text_single_page_returns_less_than_full_document(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    full_response = _upload(client_with_tmp_storage, sample_pdf_bytes)
    full_status = client_with_tmp_storage.get(
        f"/api/v1/convert/jobs/{full_response.json()['job_id']}"
    ).json()
    full_text = client_with_tmp_storage.get(full_status["download_url"]).content

    page_response = _upload(client_with_tmp_storage, sample_pdf_bytes, pages="1")
    assert page_response.status_code == 202
    page_status = client_with_tmp_storage.get(
        f"/api/v1/convert/jobs/{page_response.json()['job_id']}"
    ).json()
    page_text = client_with_tmp_storage.get(page_status["download_url"]).content

    assert len(page_text) < len(full_text)
    assert len(page_text) > 0


def test_extract_text_scanned_pdf_explains_instead_of_returning_blank_file(
    client_with_tmp_storage: TestClient,
) -> None:
    """Regression test: a PDF with no embedded text layer (e.g. a scanned
    document) used to silently produce an empty .txt file. See
    app/modules/converter/extract_text.py — the job should still complete
    (this isn't OCR), but the downloaded file must explain what happened
    rather than being blank.
    """
    doc = fitz.open()
    doc.new_page()  # a page with no text inserted — mirrors an image-only PDF
    scanned_pdf_bytes = doc.tobytes()
    doc.close()

    response = _upload(client_with_tmp_storage, scanned_pdf_bytes)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    assert status_body["status"] == "completed"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    body_text = download_response.content.decode("utf-8")
    assert body_text.strip() != ""
    assert "scanned" in body_text.lower() or "image-only" in body_text.lower()


def test_extract_text_rejects_out_of_range_page(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, sample_pdf_bytes, pages="999")
    assert response.status_code == 400
    assert "out of range" in response.json()["detail"]


def test_extract_text_rejects_corrupted_pdf(
    client_with_tmp_storage: TestClient, corrupted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, corrupted_pdf_bytes)
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]


def test_extract_text_rejects_encrypted_pdf(
    client_with_tmp_storage: TestClient, encrypted_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, encrypted_pdf_bytes)
    assert response.status_code == 400
    assert "Encrypted" in response.json()["detail"]


def test_extract_text_rejects_oversized_file(sample_pdf_bytes: bytes, tmp_path) -> None:
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
