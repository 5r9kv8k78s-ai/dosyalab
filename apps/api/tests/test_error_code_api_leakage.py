"""V2-2's `ConversionJob.error_code` (see app/services/jobs.py) is an
internal-only field — this guards that `GET /convert/jobs/{job_id}`
(`ConvertJobStatus`, see app/schemas/convert.py) never serializes it, no
matter what value it holds, and that the existing generic `error` message
contract is unchanged.
"""

from fastapi.testclient import TestClient

from app.services.failure_taxonomy import FailureCode
from app.services.jobs import JobStatus, job_store


def test_error_code_never_appears_in_job_status_response(
    client_with_tmp_storage: TestClient, tmp_path
) -> None:
    source = tmp_path / "failed.pdf"
    source.write_bytes(b"%PDF-1.4 placeholder")
    job = job_store.create(
        module_slug="pdf-to-docx", source_path=source, download_filename="failed.docx"
    )
    job_store.update(
        job.id,
        status=JobStatus.FAILED,
        error="Conversion failed. The file may use unsupported features — try a different one.",
        error_code=FailureCode.ENGINE_FAILURE,
    )

    response = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job.id}")

    assert response.status_code == 200
    body = response.json()
    assert "error_code" not in body
    assert set(body.keys()) == {"job_id", "status", "progress", "filename", "error", "download_url"}
    # The generic, pre-existing user-facing contract — unaffected by which
    # internal FailureCode this job carries.
    assert body["error"] == (
        "Conversion failed. The file may use unsupported features — try a different one."
    )


def test_error_code_absent_from_response_on_success(
    client_with_tmp_storage: TestClient, tmp_path
) -> None:
    source = tmp_path / "ok.pdf"
    source.write_bytes(b"%PDF-1.4 placeholder")
    output = tmp_path / "ok.docx"
    output.write_bytes(b"stub docx output")
    job = job_store.create(
        module_slug="pdf-to-docx", source_path=source, download_filename="ok.docx"
    )
    job_store.update(job.id, status=JobStatus.COMPLETED, progress=100, output_path=output)

    response = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job.id}")

    assert response.status_code == 200
    body = response.json()
    assert "error_code" not in body
    assert body["error"] is None
