import io

import fitz
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def _upload(client: TestClient, files: list[tuple[str, bytes, str]]):
    return client.post(
        "/api/v1/convert/merge-pdf",
        files=[
            ("files", (name, io.BytesIO(content), content_type))
            for name, content, content_type in files
        ],
    )


def test_merge_two_pdfs_success_end_to_end(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(
        client_with_tmp_storage,
        [
            ("first.pdf", sample_pdf_bytes, "application/pdf"),
            ("second.pdf", sample_pdf_bytes, "application/pdf"),
        ],
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_response = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "completed"
    assert status_body["progress"] == 100
    assert status_body["filename"] == "merged.pdf"
    assert status_body["download_url"] == f"/api/v1/convert/jobs/{job_id}/download"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.headers["content-disposition"].endswith('merged.pdf"')
    assert download_response.content[:5] == b"%PDF-"

    source_page_count = fitz.open(stream=sample_pdf_bytes, filetype="pdf").page_count
    merged_page_count = fitz.open(stream=download_response.content, filetype="pdf").page_count
    assert merged_page_count == source_page_count * 2

    # Automatic cleanup: job and its output file are gone after download.
    followup = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}")
    assert followup.status_code == 404


def test_merge_five_pdfs_success(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(
        client_with_tmp_storage,
        [(f"doc{i}.pdf", sample_pdf_bytes, "application/pdf") for i in range(5)],
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    assert status_body["status"] == "completed"
    assert status_body["filename"] == "merged.pdf"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200

    source_page_count = fitz.open(stream=sample_pdf_bytes, filetype="pdf").page_count
    merged_page_count = fitz.open(stream=download_response.content, filetype="pdf").page_count
    assert merged_page_count == source_page_count * 5


def test_merge_rejects_single_file(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, [("only.pdf", sample_pdf_bytes, "application/pdf")])
    assert response.status_code == 400
    assert "two" in response.json()["detail"].lower()


def test_merge_rejects_non_pdf_extension(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(
        client_with_tmp_storage,
        [
            ("first.pdf", sample_pdf_bytes, "application/pdf"),
            ("notes.txt", b"just some text", "text/plain"),
        ],
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_merge_rejects_empty_file(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(
        client_with_tmp_storage,
        [
            ("first.pdf", sample_pdf_bytes, "application/pdf"),
            ("empty.pdf", b"", "application/pdf"),
        ],
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_merge_rejects_corrupted_pdf(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes, corrupted_pdf_bytes: bytes
) -> None:
    response = _upload(
        client_with_tmp_storage,
        [
            ("first.pdf", sample_pdf_bytes, "application/pdf"),
            ("broken.pdf", corrupted_pdf_bytes, "application/pdf"),
        ],
    )
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]


def test_merge_rejects_encrypted_pdf(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes, encrypted_pdf_bytes: bytes
) -> None:
    response = _upload(
        client_with_tmp_storage,
        [
            ("first.pdf", sample_pdf_bytes, "application/pdf"),
            ("locked.pdf", encrypted_pdf_bytes, "application/pdf"),
        ],
    )
    assert response.status_code == 400
    assert "Encrypted" in response.json()["detail"]


def test_merge_rejects_oversized_file(sample_pdf_bytes: bytes, tmp_path) -> None:
    tiny_limit_settings = Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        max_convert_upload_size_mb=0,
    )
    app.dependency_overrides[get_settings] = lambda: tiny_limit_settings
    try:
        with TestClient(app) as client:
            response = _upload(
                client,
                [
                    ("first.pdf", sample_pdf_bytes, "application/pdf"),
                    ("second.pdf", sample_pdf_bytes, "application/pdf"),
                ],
            )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 413
