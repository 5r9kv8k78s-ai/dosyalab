import os
import re
import unicodedata
from pathlib import Path

import fitz

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_FILENAME_LENGTH = 200


class PdfValidationError(Exception):
    """Raised when an uploaded file fails PDF validation.

    `status_code` lets the endpoint translate this straight into an HTTP
    response without a separate mapping table. `error_code` is a small,
    stable category (see app/services/operations_events.py) used only for
    the privacy-safe operations event recorded alongside the HTTP response —
    never the raw `message` text, which may vary and isn't meant to be an
    analytics dimension.
    """

    def __init__(self, message: str, status_code: int = 400, error_code: str = "validation_failed"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def secure_filename(filename: str | None) -> str:
    """Reduce a client-supplied filename to a safe basename.

    Strips directory components and folds to a conservative ASCII charset so
    the result is safe to use in Content-Disposition headers, logs, and file
    paths without risking path traversal or header injection.
    """
    name = os.path.basename((filename or "").strip())
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = _SAFE_FILENAME_RE.sub("_", name).strip("._")
    if not name:
        name = "document"
    return name[:_MAX_FILENAME_LENGTH]


def validate_pdf_extension(filename: str) -> None:
    if not filename.lower().endswith(".pdf"):
        raise PdfValidationError("Only PDF files are accepted.", error_code="invalid_file_type")


def validate_pdf_size(size_bytes: int, max_size_mb: int) -> None:
    if size_bytes == 0:
        raise PdfValidationError("The uploaded file is empty.", error_code="invalid_file_type")
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise PdfValidationError(
            f"File exceeds the {max_size_mb}MB size limit.",
            status_code=413,
            error_code="file_too_large",
        )


def inspect_pdf_allow_encrypted(path: Path) -> None:
    """Confirms a file is openable as a PDF, without rejecting encrypted
    documents the way `inspect_pdf` does — used only by the unlock-pdf
    feature, whose whole point is to accept an encrypted PDF as input. A
    wrong password is caught later, during the actual unlock attempt.
    """
    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise PdfValidationError("The uploaded file is not a valid or is a corrupted PDF.") from exc
    doc.close()


def inspect_pdf(path: Path) -> int:
    """Open the PDF to confirm it is readable and unencrypted.

    Returns the page count on success; raises PdfValidationError for
    encrypted or corrupted files.
    """
    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise PdfValidationError("The uploaded file is not a valid or is a corrupted PDF.") from exc

    try:
        if doc.is_encrypted:
            raise PdfValidationError("Encrypted PDFs are not supported.")
        page_count = doc.page_count
        if page_count == 0:
            raise PdfValidationError(
                "The PDF has no readable pages — it may be empty or corrupted."
            )
        return page_count
    except PdfValidationError:
        raise
    except Exception as exc:
        raise PdfValidationError("The uploaded file is not a valid or is a corrupted PDF.") from exc
    finally:
        doc.close()
