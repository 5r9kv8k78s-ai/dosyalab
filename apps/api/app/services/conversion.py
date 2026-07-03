import asyncio
import json
import logging
import shutil
import uuid
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
from app.services.image_validation import (
    ImageValidationError,
    inspect_image,
    validate_image_extension,
    validate_image_size,
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
IMAGES_TO_PDF_SLUG = "images-to-pdf"
MERGE_PDF_SLUG = "merge-pdf"
SPLIT_PDF_SLUG = "split-pdf"
COMPRESS_PDF_SLUG = "compress-pdf"

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


async def submit_images_to_pdf_job(files: list[UploadFile], settings: Settings) -> ConversionJob:
    """Validate one or more uploaded images and create a conversion job for
    them.

    Unlike the single-file submit functions above, images are saved into a
    per-job directory rather than a single path, with a zero-padded index
    prefix on each filename — `sorted(directory.iterdir())` in
    `ImagesToPdfConverter.convert` then reproduces upload order exactly,
    since a plain directory listing isn't guaranteed to.
    """
    if not files:
        raise ImageValidationError("At least one image is required.")

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    total_size_bytes = 0
    try:
        for index, file in enumerate(files):
            original_filename = secure_filename(file.filename)
            validate_image_extension(original_filename)

            _file_id, saved_path, size_bytes = await storage.save(file)
            validate_image_size(size_bytes, settings.max_convert_upload_size_mb)
            inspect_image(saved_path)

            ordered_path = job_upload_dir / f"{index:04d}{saved_path.suffix}"
            saved_path.rename(ordered_path)
            total_size_bytes += size_bytes
    except ImageValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    if len(files) == 1:
        download_filename = f"{Path(secure_filename(files[0].filename)).stem}.pdf"
    else:
        download_filename = "images.pdf"

    job = job_store.create(
        module_slug=IMAGES_TO_PDF_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": IMAGES_TO_PDF_SLUG,
            "image_count": len(files),
            "size_bytes": total_size_bytes,
        },
    )
    return job


async def submit_merge_pdf_job(files: list[UploadFile], settings: Settings) -> ConversionJob:
    """Validate two or more uploaded PDFs and create a merge job for them.

    Mirrors `submit_images_to_pdf_job`'s directory-based ordering pattern —
    files are saved into a per-job directory with a zero-padded index prefix
    so `MergePdfConverter.convert` can reproduce upload order via a plain
    directory listing.
    """
    if len(files) < 2:
        raise PdfValidationError("At least two PDF files are required to merge.")

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    total_size_bytes = 0
    try:
        for index, file in enumerate(files):
            original_filename = secure_filename(file.filename)
            validate_pdf_extension(original_filename)

            _file_id, saved_path, size_bytes = await storage.save(file)
            validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
            inspect_pdf(saved_path)

            ordered_path = job_upload_dir / f"{index:04d}{saved_path.suffix}"
            saved_path.rename(ordered_path)
            total_size_bytes += size_bytes
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    job = job_store.create(
        module_slug=MERGE_PDF_SLUG,
        source_path=job_upload_dir,
        download_filename="merged.pdf",
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": MERGE_PDF_SLUG,
            "file_count": len(files),
            "size_bytes": total_size_bytes,
        },
    )
    return job


async def submit_split_pdf_job(
    file: UploadFile, pages_per_file: int, settings: Settings
) -> ConversionJob:
    """Validate an uploaded PDF and create a split job for it.

    `source_path` is a per-job directory containing the saved PDF plus a
    `params.json` sidecar (see `SplitPdfConverter.convert`) — the same
    directory-based convention `submit_images_to_pdf_job` and
    `submit_merge_pdf_job` use for multi-input jobs, extended here to also
    carry non-file parameters through to the converter.
    """
    if pages_per_file < 1:
        raise PdfValidationError("pages_per_file must be at least 1.")

    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    _file_id, saved_path, size_bytes = await storage.save(file)
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        inspect_pdf(saved_path)
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(json.dumps({"pages_per_file": pages_per_file}))

    download_filename = f"{Path(original_filename).stem}_split.zip"
    job = job_store.create(
        module_slug=SPLIT_PDF_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": SPLIT_PDF_SLUG,
            "pages_per_file": pages_per_file,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_compress_pdf_job(file: UploadFile, settings: Settings) -> ConversionJob:
    """Validate an uploaded PDF and create a compression job for it.

    Input format is the same as `submit_pdf_to_docx_job` (a single PDF, no
    extra parameters), so this reuses the same PDF validation helpers
    directly — only the module slug and output filename differ.
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

    download_filename = f"{Path(original_filename).stem}_compressed.pdf"
    job = job_store.create(
        module_slug=COMPRESS_PDF_SLUG,
        source_path=source_path,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": COMPRESS_PDF_SLUG,
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
        # Images-to-PDF jobs store source_path as a directory of ordered
        # image files rather than a single file (see
        # submit_images_to_pdf_job); every other converter's source_path is
        # always a plain file, so this branch is a no-op for them —
        # unlink(missing_ok=True) still runs exactly as before.
        if job.source_path.is_dir():
            shutil.rmtree(job.source_path, ignore_errors=True)
        else:
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
