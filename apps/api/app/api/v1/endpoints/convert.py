import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.core.config import Settings, get_settings
from app.schemas.convert import ConvertJobCreated, ConvertJobStatus
from app.services.conversion import (
    run_conversion_job,
    submit_compress_pdf_job,
    submit_delete_pages_job,
    submit_docx_to_pdf_job,
    submit_extract_pages_job,
    submit_images_to_pdf_job,
    submit_merge_pdf_job,
    submit_pdf_to_docx_job,
    submit_pdf_to_xlsx_job,
    submit_reorder_pages_job,
    submit_rotate_pdf_job,
    submit_split_pdf_job,
)
from app.services.docx_validation import DocxValidationError
from app.services.image_validation import ImageValidationError
from app.services.jobs import JobStatus, job_store
from app.services.pdf_validation import PdfValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/convert", tags=["convert"])

# Keyed by output file suffix rather than converter slug, so the shared
# download endpoint below stays correct for any future format without
# needing to know about individual converters.
_MEDIA_TYPE_BY_SUFFIX = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".zip": "application/zip",
    ".txt": "text/plain",
}
_DEFAULT_MEDIA_TYPE = "application/octet-stream"


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


@router.post(
    "/docx-to-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_docx_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_docx_to_pdf_job(file, settings)
    except DocxValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/pdf-to-xlsx",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_pdf_to_xlsx(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_pdf_to_xlsx_job(file, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/images-to-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_images_to_pdf(
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_images_to_pdf_job(files, settings)
    except ImageValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={
                "upload_filename": files[0].filename if files else None,
                "reason": exc.message,
            },
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/merge-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_merge_pdf(
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_merge_pdf_job(files, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={
                "upload_filename": files[0].filename if files else None,
                "reason": exc.message,
            },
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/split-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_split_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    pages_per_file: int = Form(1),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_split_pdf_job(file, pages_per_file, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/compress-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_compress_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_compress_pdf_job(file, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/rotate-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_rotate_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    rotation: int = Form(...),
    pages: str | None = Form(None),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_rotate_pdf_job(file, rotation, pages, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/delete-pages",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_delete_pages(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    pages: str = Form(...),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_delete_pages_job(file, pages, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/extract-pages",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_extract_pages(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    pages: str = Form(...),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_extract_pages_job(file, pages, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/reorder-pages",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_reorder_pages(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    order: str = Form(...),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_reorder_pages_job(file, order, settings)
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
        media_type=_media_type_for(job.output_path),
        background=BackgroundTask(_cleanup_after_download, job_id),
    )


def _media_type_for(path: Path) -> str:
    return _MEDIA_TYPE_BY_SUFFIX.get(path.suffix.lower(), _DEFAULT_MEDIA_TYPE)


def _cleanup_after_download(job_id: str) -> None:
    job = job_store.get(job_id)
    if job is None:
        return
    if job.output_path is not None:
        job.output_path.unlink(missing_ok=True)
    job_store.delete(job_id)
