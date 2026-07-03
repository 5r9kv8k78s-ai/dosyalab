import io

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.jobs import JobStatus, job_store

_DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _upload(
    client: TestClient, filename: str, content: bytes, content_type: str = _DOCX_CONTENT_TYPE
):
    return client.post(
        "/api/v1/convert/docx-to-pdf",
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


def test_convert_docx_to_pdf_success_end_to_end(
    client_with_tmp_storage: TestClient, sample_docx_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, "sample.docx", sample_docx_bytes)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_response = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "completed"
    assert status_body["progress"] == 100
    assert status_body["filename"] == "sample.pdf"
    assert status_body["download_url"] == f"/api/v1/convert/jobs/{job_id}/download"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.headers["content-disposition"].endswith('sample.pdf"')
    assert download_response.content[:5] == b"%PDF-"
    assert len(download_response.content) > 1000

    # Automatic cleanup: job and its output file are gone after download.
    followup = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}")
    assert followup.status_code == 404


def test_convert_rejects_non_docx_extension(client_with_tmp_storage: TestClient) -> None:
    response = _upload(
        client_with_tmp_storage, "notes.txt", b"just some text", content_type="text/plain"
    )
    assert response.status_code == 400
    assert "DOCX" in response.json()["detail"]


def test_convert_rejects_oversized_docx(sample_docx_bytes: bytes, tmp_path) -> None:
    tiny_limit_settings = Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        max_convert_upload_size_mb=0,
    )
    app.dependency_overrides[get_settings] = lambda: tiny_limit_settings
    try:
        with TestClient(app) as client:
            response = _upload(client, "sample.docx", sample_docx_bytes)
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 413


def test_convert_rejects_encrypted_docx(
    client_with_tmp_storage: TestClient, encrypted_docx_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, "encrypted.docx", encrypted_docx_bytes)
    assert response.status_code == 400
    assert "Encrypted" in response.json()["detail"]


def test_convert_rejects_corrupted_docx(
    client_with_tmp_storage: TestClient, corrupted_docx_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, "corrupted.docx", corrupted_docx_bytes)
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]


def test_convert_sanitizes_unsafe_filename(
    client_with_tmp_storage: TestClient, sample_docx_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, "../../etc/passwd.docx", sample_docx_bytes)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    assert status_body["filename"] == "passwd.pdf"
    assert "/" not in status_body["filename"]
    assert ".." not in status_body["filename"]


def test_download_before_completion_returns_409(
    client_with_tmp_storage: TestClient, tmp_path
) -> None:
    source = tmp_path / "in-flight.docx"
    source.write_bytes(b"PK\x03\x04placeholder")
    job = job_store.create(
        module_slug="docx-to-pdf", source_path=source, download_filename="in-flight.pdf"
    )
    job_store.update(job.id, status=JobStatus.PROCESSING, progress=40)

    response = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job.id}/download")
    assert response.status_code == 409
