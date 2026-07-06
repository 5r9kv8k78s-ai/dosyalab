import asyncio
import json
import logging
import shutil
import sys
import time
import uuid
from pathlib import Path

import fitz
from fastapi import UploadFile

from app.core.config import Settings
from app.modules.converter import ConversionModule, get_converter
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
from app.services.operations_events import classify_input_family, record_operations_event
from app.services.pdf_params import parse_page_list, validate_pages_in_range
from app.services.pdf_validation import (
    PdfValidationError,
    inspect_pdf,
    inspect_pdf_allow_encrypted,
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
ROTATE_PDF_SLUG = "rotate-pdf"
DELETE_PAGES_SLUG = "delete-pages"
EXTRACT_PAGES_SLUG = "extract-pages"
REORDER_PAGES_SLUG = "reorder-pages"
WATERMARK_PDF_SLUG = "watermark-pdf"
PROTECT_PDF_SLUG = "protect-pdf"
UNLOCK_PDF_SLUG = "unlock-pdf"
PDF_TO_IMAGES_SLUG = "pdf-to-images"
_ALLOWED_PDF_TO_IMAGE_FORMATS = {"png", "jpg", "jpeg"}
EXTRACT_IMAGES_SLUG = "extract-images"
EXTRACT_TEXT_SLUG = "extract-text"

# pdf2docx exposes no progress callback (see pdf_to_docx.py), so while the
# blocking convert() call runs in a worker thread we approximate progress by
# easing it toward a cap, leaving the final stretch for the real completion.
_PROGRESS_TICK_INTERVAL_SECONDS = 0.4
_PROGRESS_TICK_CAP = 90


# Passed as `StorageService.save`'s `on_chunk` callback so an oversized
# upload is rejected as soon as it crosses the limit mid-stream, instead of
# only after the entire file has already been written to disk (see
# storage.py). Each still raises the same typed validation error the
# existing post-save `validate_*_size` call already did, so no except
# clause needed to change.
def _pdf_size_checker(settings: Settings):
    return lambda total: validate_pdf_size(total, settings.max_convert_upload_size_mb)


def _docx_size_checker(settings: Settings):
    return lambda total: validate_docx_size(total, settings.max_convert_upload_size_mb)


def _image_size_checker(settings: Settings):
    return lambda total: validate_image_size(total, settings.max_convert_upload_size_mb)


async def submit_pdf_to_docx_job(file: UploadFile, settings: Settings) -> ConversionJob:
    """Validate an uploaded PDF and create a conversion job for it.

    The file is saved to disk first since validation (PyMuPDF) needs a real
    path to open; it is deleted again immediately on any validation failure.
    """
    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    storage = StorageService(upload_dir=settings.convert_upload_dir)
    _file_id, source_path, size_bytes = await storage.save(
        file, on_chunk=_pdf_size_checker(settings)
    )

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
    _file_id, source_path, size_bytes = await storage.save(
        file, on_chunk=_docx_size_checker(settings)
    )

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
    _file_id, source_path, size_bytes = await storage.save(
        file, on_chunk=_pdf_size_checker(settings)
    )

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
        raise ImageValidationError(
            "At least one image is required.", error_code="invalid_file_count"
        )
    if len(files) > settings.max_batch_file_count:
        raise ImageValidationError(
            f"Too many files in one request (max {settings.max_batch_file_count}).",
            error_code="batch_too_large",
        )

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    total_size_bytes = 0
    try:
        for index, file in enumerate(files):
            original_filename = secure_filename(file.filename)
            validate_image_extension(original_filename)

            _file_id, saved_path, size_bytes = await storage.save(
                file, on_chunk=_image_size_checker(settings)
            )
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
        file_count=len(files),
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
        raise PdfValidationError(
            "At least two PDF files are required to merge.", error_code="invalid_file_count"
        )
    if len(files) > settings.max_batch_file_count:
        raise PdfValidationError(
            f"Too many files in one request (max {settings.max_batch_file_count}).",
            error_code="batch_too_large",
        )

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    total_size_bytes = 0
    try:
        for index, file in enumerate(files):
            original_filename = secure_filename(file.filename)
            validate_pdf_extension(original_filename)

            _file_id, saved_path, size_bytes = await storage.save(
                file, on_chunk=_pdf_size_checker(settings)
            )
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
        file_count=len(files),
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

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
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
    _file_id, source_path, size_bytes = await storage.save(
        file, on_chunk=_pdf_size_checker(settings)
    )

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


async def submit_rotate_pdf_job(
    file: UploadFile, rotation: int, pages: str | None, settings: Settings
) -> ConversionJob:
    """Validate an uploaded PDF and create a rotation job for it.

    Follows the same directory + `params.json` convention as
    `submit_split_pdf_job` — `pages` is 1-indexed from the API's
    perspective and parsed/validated via `app.services.pdf_params` before
    being stored 0-indexed for `PdfEngine.rotate_pdf`. `None` rotates every
    page.
    """
    if rotation % 90 != 0:
        raise PdfValidationError("rotation must be a multiple of 90 degrees.")

    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        page_count = inspect_pdf(saved_path)
        zero_indexed_pages = parse_page_list(pages, field_name="pages")
        if zero_indexed_pages is not None:
            validate_pages_in_range(zero_indexed_pages, page_count, field_name="pages")
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(
        json.dumps({"rotation": rotation, "pages": zero_indexed_pages})
    )

    download_filename = f"{Path(original_filename).stem}_rotated.pdf"
    job = job_store.create(
        module_slug=ROTATE_PDF_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": ROTATE_PDF_SLUG,
            "rotation": rotation,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_delete_pages_job(
    file: UploadFile, pages: str, settings: Settings
) -> ConversionJob:
    """Validate an uploaded PDF and create a delete-pages job for it.

    `pages` is a required, 1-indexed comma-separated list — at least one
    page must be selected, and deleting every page is rejected.
    """
    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        page_count = inspect_pdf(saved_path)
        zero_indexed_pages = parse_page_list(pages, field_name="pages")
        if not zero_indexed_pages:
            raise PdfValidationError("At least one page must be specified.")
        validate_pages_in_range(zero_indexed_pages, page_count, field_name="pages")
        if len(set(zero_indexed_pages)) >= page_count:
            raise PdfValidationError("Cannot delete all pages from a PDF.")
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(json.dumps({"pages": zero_indexed_pages}))

    download_filename = f"{Path(original_filename).stem}_edited.pdf"
    job = job_store.create(
        module_slug=DELETE_PAGES_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": DELETE_PAGES_SLUG,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_extract_pages_job(
    file: UploadFile, pages: str, settings: Settings
) -> ConversionJob:
    """Validate an uploaded PDF and create an extract-pages job for it.

    `pages` is a required, 1-indexed comma-separated list — order and
    duplicates are preserved exactly as given, since `PdfEngine.extract_pages`
    uses them directly to build the new document's page order.
    """
    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        page_count = inspect_pdf(saved_path)
        zero_indexed_pages = parse_page_list(pages, field_name="pages")
        if not zero_indexed_pages:
            raise PdfValidationError("At least one page must be specified.")
        validate_pages_in_range(zero_indexed_pages, page_count, field_name="pages")
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(json.dumps({"pages": zero_indexed_pages}))

    download_filename = f"{Path(original_filename).stem}_extracted.pdf"
    job = job_store.create(
        module_slug=EXTRACT_PAGES_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": EXTRACT_PAGES_SLUG,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_reorder_pages_job(
    file: UploadFile, order: str, settings: Settings
) -> ConversionJob:
    """Validate an uploaded PDF and create a reorder-pages job for it.

    `order` is a required, 1-indexed comma-separated permutation of every
    page in the document — a subset or duplicate list is rejected here
    before the job even starts, mirroring the check `PdfEngine.reorder_pages`
    performs itself.
    """
    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        page_count = inspect_pdf(saved_path)
        zero_indexed_order = parse_page_list(order, field_name="order")
        if not zero_indexed_order:
            raise PdfValidationError("order must not be empty.")
        validate_pages_in_range(zero_indexed_order, page_count, field_name="order")
        if len(zero_indexed_order) != page_count or set(zero_indexed_order) != set(
            range(page_count)
        ):
            raise PdfValidationError("order must be a permutation of every page in the document.")
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(json.dumps({"order": zero_indexed_order}))

    download_filename = f"{Path(original_filename).stem}_reordered.pdf"
    job = job_store.create(
        module_slug=REORDER_PAGES_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": REORDER_PAGES_SLUG,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_watermark_pdf_job(
    file: UploadFile,
    text: str,
    opacity: float,
    font_size: int,
    rotation: float,
    settings: Settings,
) -> ConversionJob:
    """Validate an uploaded PDF and create a watermark job for it."""
    if not text.strip():
        raise PdfValidationError("Watermark text must not be empty.")

    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        inspect_pdf(saved_path)
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(
        json.dumps({"text": text, "opacity": opacity, "font_size": font_size, "rotation": rotation})
    )

    download_filename = f"{Path(original_filename).stem}_watermarked.pdf"
    job = job_store.create(
        module_slug=WATERMARK_PDF_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": WATERMARK_PDF_SLUG,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_protect_pdf_job(
    file: UploadFile, user_password: str, owner_password: str | None, settings: Settings
) -> ConversionJob:
    """Validate an uploaded PDF and create a protect job for it.

    Rejects already-encrypted input via the normal `inspect_pdf` check —
    unlock it first (see `submit_unlock_pdf_job`) before protecting it with
    a new password.
    """
    if not user_password:
        raise PdfValidationError("A user password is required to protect a PDF.")

    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        inspect_pdf(saved_path)
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(
        json.dumps({"user_password": user_password, "owner_password": owner_password})
    )

    download_filename = f"{Path(original_filename).stem}_protected.pdf"
    job = job_store.create(
        module_slug=PROTECT_PDF_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": PROTECT_PDF_SLUG,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_unlock_pdf_job(
    file: UploadFile, password: str, settings: Settings
) -> ConversionJob:
    """Validate an uploaded PDF and create an unlock job for it.

    Unlike every other PDF-accepting submit function, this one uses
    `inspect_pdf_allow_encrypted` instead of `inspect_pdf` — accepting an
    encrypted PDF is the entire point of this feature. A wrong password is
    caught later, inside the job, by `PdfEngine.unlock_pdf` itself, and
    surfaces as a failed job rather than a validation error here.
    """
    if not password:
        raise PdfValidationError("A password is required to unlock a PDF.")

    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        inspect_pdf_allow_encrypted(saved_path)
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(json.dumps({"password": password}))

    download_filename = f"{Path(original_filename).stem}_unlocked.pdf"
    job = job_store.create(
        module_slug=UNLOCK_PDF_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": UNLOCK_PDF_SLUG,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_pdf_to_images_job(
    file: UploadFile, image_format: str, dpi: int, settings: Settings
) -> ConversionJob:
    """Validate an uploaded PDF and create a pdf-to-images job for it."""
    normalized_format = image_format.lower().lstrip(".")
    if normalized_format not in _ALLOWED_PDF_TO_IMAGE_FORMATS:
        raise PdfValidationError(f"Unsupported image format: {image_format!r}.")
    if dpi < 1:
        raise PdfValidationError("dpi must be a positive integer.")

    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        inspect_pdf(saved_path)
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(
        json.dumps({"image_format": normalized_format, "dpi": dpi})
    )

    download_filename = f"{Path(original_filename).stem}_pages.zip"
    job = job_store.create(
        module_slug=PDF_TO_IMAGES_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": PDF_TO_IMAGES_SLUG,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_extract_images_job(file: UploadFile, settings: Settings) -> ConversionJob:
    """Validate an uploaded PDF and create an extract-images job for it.

    Input format is the same as `submit_compress_pdf_job` (a single PDF, no
    extra parameters). Whether the PDF actually contains any embedded
    images is only known once the job runs, so that check lives in
    `ExtractImagesConverter.convert`, not here.
    """
    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    storage = StorageService(upload_dir=settings.convert_upload_dir)
    _file_id, source_path, size_bytes = await storage.save(
        file, on_chunk=_pdf_size_checker(settings)
    )

    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        page_count = inspect_pdf(source_path)
    except PdfValidationError:
        source_path.unlink(missing_ok=True)
        raise

    download_filename = f"{Path(original_filename).stem}_images.zip"
    job = job_store.create(
        module_slug=EXTRACT_IMAGES_SLUG,
        source_path=source_path,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": EXTRACT_IMAGES_SLUG,
            "pages": page_count,
            "size_bytes": size_bytes,
        },
    )
    return job


async def submit_extract_text_job(
    file: UploadFile, pages: str | None, settings: Settings
) -> ConversionJob:
    """Validate an uploaded PDF and create an extract-text job for it.

    `pages` is optional and 1-indexed; omitted means every page.
    """
    original_filename = secure_filename(file.filename)
    validate_pdf_extension(original_filename)

    job_upload_dir = settings.convert_upload_dir / uuid.uuid4().hex
    storage = StorageService(upload_dir=job_upload_dir)

    try:
        _file_id, saved_path, size_bytes = await storage.save(
            file, on_chunk=_pdf_size_checker(settings)
        )
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise
    try:
        validate_pdf_size(size_bytes, settings.max_convert_upload_size_mb)
        page_count = inspect_pdf(saved_path)
        zero_indexed_pages = parse_page_list(pages, field_name="pages")
        if zero_indexed_pages is not None:
            validate_pages_in_range(zero_indexed_pages, page_count, field_name="pages")
    except PdfValidationError:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise

    saved_path.rename(job_upload_dir / "source.pdf")
    (job_upload_dir / "params.json").write_text(json.dumps({"pages": zero_indexed_pages}))

    download_filename = f"{Path(original_filename).stem}.txt"
    job = job_store.create(
        module_slug=EXTRACT_TEXT_SLUG,
        source_path=job_upload_dir,
        download_filename=download_filename,
    )
    logger.info(
        "convert.job_created",
        extra={
            "job_id": job.id,
            "converter_slug": EXTRACT_TEXT_SLUG,
            "size_bytes": size_bytes,
        },
    )
    return job


def _pdf_complexity_metrics(source_path: Path) -> dict[str, int]:
    """Best-effort, privacy-safe structural metadata for a PDF, computed
    just before a pdf-to-docx conversion starts — used only to diagnose why
    some PDF→Word jobs hang in production (stuck in PROCESSING) while others
    complete normally (see the `convert.convert_started` log below).

    Raises on any PyMuPDF failure — callers must treat that as "metadata
    unavailable" and let the conversion proceed regardless; this must never
    gate, delay, or otherwise change conversion behavior.
    """
    total_images = 0
    total_drawings = 0
    text_char_count = 0
    with fitz.open(source_path) as doc:
        page_count = doc.page_count
        for page in doc:
            total_images += len(page.get_images(full=True))
            total_drawings += len(page.get_drawings())
            text_char_count += len(page.get_text("text"))
    return {
        "page_count": page_count,
        "file_size_bytes": source_path.stat().st_size,
        "total_images": total_images,
        "total_drawings": total_drawings,
        "text_char_count": text_char_count,
    }


# Grace period between asking a stuck conversion process to exit (terminate,
# i.e. SIGTERM) and giving up on that and forcing it (kill, i.e. SIGKILL).
# Not user-configurable — this is an internal implementation detail of how
# long we're willing to wait for a clean shutdown, not a policy knob.
_TERMINATE_GRACE_PERIOD_SECONDS = 5


class ConversionSubprocessError(Exception):
    """A conversion subprocess (see `_run_worker_subprocess`) exited with a
    non-zero code, or was killed after exceeding its timeout."""


async def _run_worker_subprocess(
    args: list[str],
    *,
    timeout_seconds: float,
    job_id: str,
    tool_slug: str,
) -> str:
    """Runs `args` (already including the interpreter — never with a shell)
    as a real OS subprocess, enforcing a hard timeout. Unlike a worker
    thread (`asyncio.to_thread`), a process that exceeds `timeout_seconds`
    is genuinely terminated — or killed, if it ignores that — and reaped;
    it is never left running in the background consuming CPU/memory or
    occupying a shared thread pool slot other conversions need.

    Returns the subprocess's stdout, decoded and stripped, on a zero exit
    code. Raises `ConversionSubprocessError` for a non-zero exit code or a
    timeout — in the timeout case, only after the process has actually
    been terminated/killed and reaped.
    """
    started_at = time.monotonic()
    logger.info(
        "convert.process_started",
        extra={"job_id": job_id, "tool_slug": tool_slug, "timeout_seconds": timeout_seconds},
    )

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        # Never captured/logged/surfaced — a worker's traceback could
        # incidentally include the source file path, which must never
        # reach any log or the user. The exit code is the only signal
        # the parent needs to detect failure.
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError:
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        logger.warning(
            "convert.process_timeout",
            extra={
                "job_id": job_id,
                "tool_slug": tool_slug,
                "elapsed_ms": elapsed_ms,
                "timeout_seconds": timeout_seconds,
            },
        )
        await _terminate_then_kill(process, job_id=job_id, tool_slug=tool_slug)
        raise ConversionSubprocessError(
            f"Conversion subprocess exceeded {timeout_seconds}s timeout."
        ) from None

    elapsed_ms = int((time.monotonic() - started_at) * 1000)
    logger.info(
        "convert.process_completed",
        extra={
            "job_id": job_id,
            "tool_slug": tool_slug,
            "elapsed_ms": elapsed_ms,
            "exit_code": process.returncode,
        },
    )
    if process.returncode != 0:
        raise ConversionSubprocessError(
            f"Conversion subprocess exited with code {process.returncode}."
        )
    return stdout.decode().strip()


async def _terminate_then_kill(
    process: asyncio.subprocess.Process, *, job_id: str, tool_slug: str
) -> None:
    """Asks `process` to exit, escalating to a forced kill — and reaping it
    either way — if it doesn't within the grace period."""
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=_TERMINATE_GRACE_PERIOD_SECONDS)
        logger.warning(
            "convert.process_terminated",
            extra={"job_id": job_id, "tool_slug": tool_slug, "termination_method": "terminate"},
        )
    except TimeoutError:
        process.kill()
        await process.wait()  # reap — must not leave a zombie process behind
        logger.warning(
            "convert.process_killed",
            extra={"job_id": job_id, "tool_slug": tool_slug, "termination_method": "kill"},
        )


async def _convert_pdf_to_docx_isolated(
    job_id: str, source_path: Path, destination_dir: Path, timeout_seconds: float
) -> Path:
    """Runs the real `PdfToDocxConverter` (non-RGB image compatibility fix
    included, since this imports and uses the exact same module) in its own
    process — see `pdf_to_docx_worker.py`. Only pdf-to-docx uses process
    isolation; every other converter still runs via `asyncio.to_thread`
    below."""
    stdout_text = await _run_worker_subprocess(
        [
            sys.executable,
            "-m",
            "app.services.pdf_to_docx_worker",
            str(source_path),
            str(destination_dir),
        ],
        timeout_seconds=timeout_seconds,
        job_id=job_id,
        tool_slug=PDF_TO_DOCX_SLUG,
    )
    return Path(stdout_text)


async def _convert_with_timeout(
    converter: ConversionModule, job: ConversionJob, settings: Settings, timeout_seconds: float
) -> Path:
    """Runs `converter.convert` in a worker thread with a hard ceiling — for
    converters where a real OS process (see `_convert_pdf_to_docx_isolated`)
    was judged unnecessary, but an unbounded worker thread still isn't
    acceptable. Unlike a subprocess, the underlying thread cannot actually
    be killed and keeps running after this raises; the point is only to
    release the job as FAILED promptly instead of leaving it in PROCESSING
    forever, not to reclaim the thread pool slot early.
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(converter.convert, job.source_path, settings.convert_output_dir),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        logger.warning(
            "convert.thread_timeout",
            extra={
                "job_id": job.id,
                "tool_slug": job.module_slug,
                "timeout_seconds": timeout_seconds,
            },
        )
        raise


async def run_conversion_job(job_id: str, settings: Settings) -> None:
    """Run the registered converter for a job in a worker thread, tracking
    progress — and the one shared point every tool's actual conversion
    outcome passes through, regardless of which of the 17 endpoints
    submitted it. This is where the operations event's `success`/`failure`
    row is recorded (see app/services/operations_events.py), with
    `duration_ms` measuring the real conversion work below, not the
    upload/validation time already spent before this background task started.
    """
    job = job_store.get(job_id)
    if job is None:
        return

    job_store.update(job_id, status=JobStatus.PROCESSING, progress=10)
    ticker = asyncio.create_task(_tick_progress(job_id))
    started_at = time.monotonic()

    try:
        converter = get_converter(job.module_slug)
        if converter is None:
            raise RuntimeError(f"No converter registered for slug '{job.module_slug}'")

        # Diagnostic-only instrumentation: pins down whether a stuck job is
        # actually waiting on this specific call (never logs CONVERT_RETURNED/
        # CONVERT_RAISED) versus something elsewhere in this function — no
        # filename, path, or other user data, just the job/tool identifiers
        # already used by the surrounding logger.info calls.
        convert_started_at = time.monotonic()
        log_extra: dict[str, object] = {"job_id": job_id, "tool_slug": job.module_slug}
        if job.module_slug == PDF_TO_DOCX_SLUG:
            # Structural complexity metrics — only for pdf-to-docx, the tool
            # actually seen hanging in production — to compare a stuck job's
            # source PDF against a successful one's. Fail-open: a metrics
            # failure only skips these fields, it never affects conversion.
            try:
                log_extra.update(_pdf_complexity_metrics(job.source_path))
            except Exception as exc:
                logger.warning(
                    "convert.complexity_metrics_failed",
                    extra={
                        "job_id": job_id,
                        "tool_slug": job.module_slug,
                        "exception_type": type(exc).__name__,
                    },
                )
        logger.info("convert.convert_started", extra=log_extra)
        try:
            if job.module_slug == PDF_TO_DOCX_SLUG:
                # Killable process isolation + hard timeout — see
                # _convert_pdf_to_docx_isolated. Every other converter still
                # runs via the plain worker-thread path below, unchanged.
                output_path = await _convert_pdf_to_docx_isolated(
                    job_id,
                    job.source_path,
                    settings.convert_output_dir,
                    settings.pdf_to_docx_conversion_timeout_seconds,
                )
            elif job.module_slug == DOCX_TO_PDF_SLUG:
                # xhtml2pdf (pure-Python HTML/CSS rendering) has no bound on
                # how long it can run — see _convert_with_timeout.
                output_path = await _convert_with_timeout(
                    converter, job, settings, settings.docx_to_pdf_conversion_timeout_seconds
                )
            else:
                output_path = await asyncio.to_thread(
                    converter.convert, job.source_path, settings.convert_output_dir
                )
        except Exception:
            logger.exception(
                "convert.convert_raised",
                extra={
                    "job_id": job_id,
                    "tool_slug": job.module_slug,
                    "elapsed_ms": int((time.monotonic() - convert_started_at) * 1000),
                },
            )
            raise
        logger.info(
            "convert.convert_returned",
            extra={
                "job_id": job_id,
                "tool_slug": job.module_slug,
                "elapsed_ms": int((time.monotonic() - convert_started_at) * 1000),
            },
        )
        job_store.update(job_id, status=JobStatus.COMPLETED, progress=100, output_path=output_path)
        logger.info("convert.job_completed", extra={"job_id": job_id})
        # record_operations_event is a synchronous (blocking) Postgres write
        # when OPERATIONS_STORE_BACKEND=postgres — the job above is already
        # marked COMPLETED, but calling this directly (un-threaded) would
        # still block this single-worker process's entire event loop for
        # its duration, freezing every other in-flight request (including
        # the frontend's own job-status polling) until it returns. Running
        # it in a worker thread, the same pattern already used for
        # converter.convert() above, keeps the loop free regardless of how
        # slow/unresponsive the database connection is.
        await asyncio.to_thread(
            record_operations_event,
            event_type="conversion",
            tool_slug=job.module_slug,
            status="success",
            file_count=job.file_count,
            input_family=classify_input_family(job.module_slug),
            duration_ms=int((time.monotonic() - started_at) * 1000),
            error_code=None,
            settings=settings,
        )
    except Exception:
        job_store.update(
            job_id,
            status=JobStatus.FAILED,
            error="Conversion failed. The file may use unsupported features — try a different one.",
        )
        logger.exception("convert.job_failed", extra={"job_id": job_id})
        await asyncio.to_thread(
            record_operations_event,
            event_type="conversion",
            tool_slug=job.module_slug,
            status="failure",
            file_count=job.file_count,
            input_family=classify_input_family(job.module_slug),
            duration_ms=int((time.monotonic() - started_at) * 1000),
            error_code="conversion_failed",
            settings=settings,
        )
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
