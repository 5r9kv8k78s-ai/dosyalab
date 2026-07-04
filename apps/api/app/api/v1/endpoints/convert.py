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
    submit_extract_images_job,
    submit_extract_pages_job,
    submit_extract_text_job,
    submit_images_to_pdf_job,
    submit_merge_pdf_job,
    submit_pdf_to_docx_job,
    submit_pdf_to_images_job,
    submit_pdf_to_xlsx_job,
    submit_protect_pdf_job,
    submit_reorder_pages_job,
    submit_rotate_pdf_job,
    submit_split_pdf_job,
    submit_unlock_pdf_job,
    submit_watermark_pdf_job,
)
from app.services.docx_validation import DocxValidationError
from app.services.image_validation import ImageValidationError
from app.services.jobs import JobStatus, job_store
from app.services.operations_events import classify_input_family, record_operations_event
from app.services.pdf_validation import PdfValidationError
from app.services.rate_limiter import enforce_conversion_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/convert", tags=["convert"])

# Applied to every conversion/upload route below (not to health, robots,
# sitemap, or static asset routes — those aren't the expensive operation
# this protects). See app/services/rate_limiter.py for the algorithm and
# its documented process-local/fixed-window limitations.
_RATE_LIMITED = [Depends(enforce_conversion_rate_limit)]

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
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="pdf-to-docx",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("pdf-to-docx"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/docx-to-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="docx-to-pdf",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("docx-to-pdf"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/pdf-to-xlsx",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="pdf-to-xlsx",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("pdf-to-xlsx"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/images-to-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="images-to-pdf",
            status="validation_rejected",
            file_count=len(files),
            input_family=classify_input_family("images-to-pdf"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/merge-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="merge-pdf",
            status="validation_rejected",
            file_count=len(files),
            input_family=classify_input_family("merge-pdf"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/split-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="split-pdf",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("split-pdf"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/compress-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="compress-pdf",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("compress-pdf"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/rotate-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="rotate-pdf",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("rotate-pdf"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/delete-pages",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="delete-pages",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("delete-pages"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/extract-pages",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="extract-pages",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("extract-pages"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/reorder-pages",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
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
        record_operations_event(
            event_type="conversion",
            tool_slug="reorder-pages",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("reorder-pages"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/watermark-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
)
async def convert_watermark_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    text: str = Form(...),
    opacity: float = Form(0.3),
    font_size: int = Form(40),
    rotation: float = Form(45.0),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_watermark_pdf_job(file, text, opacity, font_size, rotation, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        record_operations_event(
            event_type="conversion",
            tool_slug="watermark-pdf",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("watermark-pdf"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/protect-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
)
async def convert_protect_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    user_password: str = Form(...),
    owner_password: str | None = Form(None),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_protect_pdf_job(file, user_password, owner_password, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        record_operations_event(
            event_type="conversion",
            tool_slug="protect-pdf",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("protect-pdf"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/unlock-pdf",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
)
async def convert_unlock_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    password: str = Form(...),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_unlock_pdf_job(file, password, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        record_operations_event(
            event_type="conversion",
            tool_slug="unlock-pdf",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("unlock-pdf"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/pdf-to-images",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
)
async def convert_pdf_to_images(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    image_format: str = Form("png"),
    dpi: int = Form(150),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_pdf_to_images_job(file, image_format, dpi, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        record_operations_event(
            event_type="conversion",
            tool_slug="pdf-to-images",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("pdf-to-images"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/extract-images",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
)
async def convert_extract_images(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_extract_images_job(file, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        record_operations_event(
            event_type="conversion",
            tool_slug="extract-images",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("extract-images"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(run_conversion_job, job.id, settings)
    return ConvertJobCreated(job_id=job.id, status=job.status)


@router.post(
    "/extract-text",
    response_model=ConvertJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=_RATE_LIMITED,
)
async def convert_extract_text(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    pages: str | None = Form(None),
    settings: Settings = Depends(get_settings),
) -> ConvertJobCreated:
    try:
        job = await submit_extract_text_job(file, pages, settings)
    except PdfValidationError as exc:
        logger.warning(
            "convert.validation_failed",
            extra={"upload_filename": file.filename, "reason": exc.message},
        )
        record_operations_event(
            event_type="conversion",
            tool_slug="extract-text",
            status="validation_rejected",
            file_count=1,
            input_family=classify_input_family("extract-text"),
            duration_ms=None,
            error_code=getattr(exc, "error_code", "validation_failed"),
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
