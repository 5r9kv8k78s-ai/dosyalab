import asyncio
import logging
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.modules.converter import get_converter
from app.services.docx_validation import (
    DocxValidationError,
    inspect_docx,
    validate_docx_extension,
    validate_docx_size,
)
from app.services.jobs import ConversionJob, JobStatus, job_store
from app.services.pdf_validation import (
    PdfValidationError,
    inspect_pdf,
    secure_filename,
    validate_pdf_extension,
    validate_pdf_size,
)
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

PDF_TO_DOCX_SLUG = "pdf-to-docx"
DOCX_TO_PDF_SLUG = "docx-to-pdf"
PDF_TO_XLSX_SLUG = "pdf-to-xlsx"

# pdf2docx exposes no progress callback (see pdf_to_docx.py), so while the
# blocking convert() call runs in a worker thread we approximate progress by
# easing it toward a cap, leaving the final stretch for the real completion.
_PROGRESS_TICK_INTERVAL_SECONDS = 0.4
_PROGRESS_TICK_CAP = 90


async def submit_pdf_to_docx_job(file: UploadFile, settings: Settings) -> ConversionJob:
    """Validate an uploaded PDF and create a conversion job for it.

    The file is saved to disk first since validation (PyMuPDF) needs a real
    path to open; it is deleted again immediately on any validation failure.
    """
    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    storage = StorageService(upload_dir=settings.convert_upload_dir)
    _file_id, source_path, size_bytes = await storage.save(file)

    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        page_count = inspect_pdf(source_path)
    except PdfValidationError:
        source_path.unlink(missing_ok=True)
        raise

    download_filename = f"{Path(original_filename).stem}.docx"
    job = job_store.create(
        module_slug=PDF_TO_DOCX_SLUG,
        source_path=source_path,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": PDF_TO_DOCX_SLUG,
            "pages": page_count,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_docx_to_pdf_job(file: UploadFile, settings: Settings) -> ConversionJob:
    """Validate an uploaded DOCX and create a conversion job for it.

    Mirrors `submit_pdf_to_docx_job` above — same storage/validation/job-store
    pattern, swapped for DOCX-specific checks.
    """
    original_filename = secure_filename(file.filename)
    validate_docx_extension(original_filename)

    storage = StorageService(upload_dir=settings.convert_upload_dir)
    _file_id, source_path, size_bytes = await storage.save(file)

    try:
        validate_docx_size(size_bytes, settings.max_convert_upload_size_mb)
        paragraph_count = inspect_docx(source_path)
    except DocxValidationError:
        source_path.unlink(missing_ok=True)
        raise

    download_filename = f"{Path(original_filename).stem}.pdf"
    job = job_store.create(
        module_slug=DOCX_TO_PDF_SLUG,
        source_path=source_path,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": DOCX_TO_PDF_SLUG,
            "paragraphs": paragraph_count,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_pdf_to_xlsx_job(file: UploadFile, settings: Settings) -> ConversionJob:
    """Validate an uploaded PDF and create a conversion job for it.

    Input format is the same as `submit_pdf_to_docx_job` (PDF), so this
    reuses the same PDF validation helpers directly rather than duplicating
    them — only the module slug and output extension differ.
    """
    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    storage = StorageService(upload_dir=settings.convert_upload_dir)
    _file_id, source_path, size_bytes = await storage.save(file)

    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        page_count = inspect_pdf(source_path)
    except PdfValidationError:
        source_path.unlink(missing_ok=True)
        raise

    download_filename = f"{Path(original_filename).stem}.xlsx"
    job = job_store.create(
        module_slug=PDF_TO_XLSX_SLUG,
        source_path=source_path,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": PDF_TO_XLSX_SLUG,
            "pages": page_count,
            "size_bytes": size_bytes,
        },
    )
    return job


async def run_conversion_job(job_id: str, settings: Settings) -> None:
    """Run the registered converter for a job in a worker thread, tracking progress."""
    job = job_store.get(job_id)
    if job is None:
        return

    job_store.update(job_id, status=JobStatus.PROCESSING, progress=10)
    ticker = asyncio.create_task(_tick_progress(job_id))

    try:
        converter = get_converter(job.module_slug)
        if converter is None:
            raise RuntimeError(f"No converter registered for slug '{job.module_slug}'")

        output_path = await asyncio.to_thread(
            converter.convert, job.source_path, settings.convert_output_dir
        )
        job_store.update(job_id, status=JobStatus.COMPLETED, progress=100, output_path=output_path)
        logger.info("convert.job_completed", extra={"job_id": job_id})
    except Exception:
        job_store.update(
            job_id,
            status=JobStatus.FAILED,
            error="Conversion failed. The file may use unsupported features — try a different one.",
        )
        logger.exception("convert.job_failed", extra={"job_id": job_id})
    finally:
        ticker.cancel()
        job.source_path.unlink(missing_ok=True)


async def _tick_progress(job_id: str) -> None:
    try:
        while True:
            await asyncio.sleep(_PROGRESS_TICK_INTERVAL_SECONDS)
            job = job_store.get(job_id)
            if job is None or job.status != JobStatus.PROCESSING:
                return
            step = max(1, int((_PROGRESS_TICK_CAP - job.progress) * 0.15))
            job_store.update(job_id, progress=min(job.progress + step, _PROGRESS_TICK_CAP))
    except asyncio.CancelledError:
        pass
