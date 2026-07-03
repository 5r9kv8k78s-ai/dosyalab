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

    _file_id, saved_path, size_bytes = await storage.save(file)
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

    _file_id, saved_path, size_bytes = await storage.save(file)
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

    _file_id, saved_path, size_bytes = await storage.save(file)
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

    _file_id, saved_path, size_bytes = await storage.save(file)
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

    _file_id, saved_path, size_bytes = await storage.save(file)
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

    _file_id, saved_path, size_bytes = await storage.save(file)
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

    _file_id, saved_path, size_bytes = await storage.save(file)
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

    _file_id, saved_path, size_bytes = await storage.save(file)
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
    _file_id, source_path, size_bytes = await storage.save(file)

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
