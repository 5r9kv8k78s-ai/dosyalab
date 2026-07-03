import io

import fitz
from fastapi.testclient import TestClient


def _upload(
    client: TestClient, filename: str, content: bytes, content_type: str = "application/pdf"
):
    return client.post(
        "/api/v1/convert/pdf-to-xlsx",
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


def test_convert_pdf_to_xlsx_success_end_to_end(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, "sample.pdf", sample_pdf_bytes)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_response = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "completed"
    assert status_body["progress"] == 100
    assert status_body["filename"] == "sample.xlsx"
    assert status_body["download_url"] == f"/api/v1/convert/jobs/{job_id}/download"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert download_response.headers["content-disposition"].endswith('sample.xlsx"')
    assert download_response.content[:2] == b"PK"  # an .xlsx is a zip archive
    assert len(download_response.content) > 1000

    # Automatic cleanup: job and its output file are gone after download.
    followup = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}")
    assert followup.status_code == 404


def test_convert_rejects_non_pdf_extension(client_with_tmp_storage: TestClient) -> None:
    response = _upload(
        client_with_tmp_storage, "notes.txt", b"just some text", content_type="text/plain"
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_convert_job_fails_when_no_tables_found(
    client_with_tmp_storage: TestClient, sample_pdf_path
) -> None:
    # A real single-page subset of the fixture (page 1 has no tables,
    # verified with find_tables() in test_pdf_to_xlsx_converter.py).
    source = fitz.open(sample_pdf_path)
    single_page = fitz.open()
    single_page.insert_pdf(source, from_page=0, to_page=0)
    no_tables_bytes = single_page.tobytes()
    single_page.close()
    source.close()

    response = _upload(client_with_tmp_storage, "no-tables.pdf", no_tables_bytes)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    assert status_body["status"] == "failed"
    assert status_body["error"]
