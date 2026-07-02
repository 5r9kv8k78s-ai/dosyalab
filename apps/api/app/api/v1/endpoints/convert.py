import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.core.config import Settings, get_settings
from app.schemas.convert import ConvertJobCreated, ConvertJobStatus
from app.services.conversion import run_conversion_job, submit_pdf_to_docx_job
from app.services.jobs import JobStatus, job_store
from app.services.pdf_validation import PdfValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/convert", tags=["convert"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post(
    "/pdf-to-docx",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_pdf_to_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_pdf_to_docx_job(file, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=ConvertJobStatus)
def get_conversion_status(
    job_id: str, settings: Settings = Depends(get_settings)
) -> ConvertJobStatus:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Conversion job not found.")

    download_url = (
        f"{settings.api_v1_prefix}/convert/jobs/{job_id}/download"
        if job.status == JobStatus.COMPLETED
        else None
    )
    return ConvertJobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        filename=job.download_filename,
        error=job.error,
        download_url=download_url,
    )


@router.get("/jobs/{job_id}/download")
def download_conversion_result(job_id: str) -> FileResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Conversion job not found.")
    if job.status != JobStatus.COMPLETED or job.output_path is None:
        raise HTTPException(status_code=409, detail="Conversion is not finished yet.")

    return FileResponse(
        path=job.output_path,
        filename=job.download_filename,
        media_type=DOCX_MEDIA_TYPE,
        background=BackgroundTask(_cleanup_after_download, job_id),
    )


def _cleanup_after_download(job_id: str) -> None:
    job = job_store.get(job_id)
    if job is None:
        return
    if job.output_path is not None:
        job.output_path.unlink(missing_ok=True)
    job_store.delete(job_id)
