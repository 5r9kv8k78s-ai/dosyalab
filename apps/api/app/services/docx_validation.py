from pathlib import Path

import docx

# Re-exported rather than duplicated: this function has no PDF-specific
# logic (just filename sanitization), so it's shared as-is across converters.
from app.services.pdf_validation import secure_filename  # noqa: F401

# Password-protected OOXML files (.docx/.xlsx/.pptx) are wrapped in an MS-CFB
# (Compound File Binary) container instead of being a plain ZIP archive, so
# they start with this fixed 8-byte signature instead of the ZIP local file
# header "PK\x03\x04". This lets us distinguish "encrypted" from "corrupted"
# up front, the same way PdfValidationError does for encrypted PDFs.
_OLE_COMPOUND_FILE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_MAX_FILENAME_LENGTH = 200


class DocxValidationError(Exception):
    """Raised when an uploaded file fails DOCX validation.

    `status_code` lets the endpoint translate this straight into an HTTP
    response without a separate mapping table.
    """

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_docx_extension(filename: str) -> None:
    if not filename.lower().endswith(".docx"):
        raise DocxValidationError("Only DOCX files are accepted.")


def validate_docx_size(size_bytes: int, max_size_mb: int) -> None:
    if size_bytes == 0:
        raise DocxValidationError("The uploaded file is empty.")
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise DocxValidationError(f"File exceeds the {max_size_mb}MB size limit.", status_code=413)


def inspect_docx(path: Path) -> int:
    """Open the DOCX to confirm it is readable and unencrypted.

    Returns the paragraph count on success; raises DocxValidationError for
    encrypted or corrupted files.
    """
    with open(path, "rb") as f:
        header = f.read(8)
    if header == _OLE_COMPOUND_FILE_SIGNATURE:
        raise DocxValidationError("Encrypted DOCX files are not supported.")

    try:
        document = docx.Document(path)
    except Exception as exc:
        raise DocxValidationError(
            "The uploaded file is not a valid or is a corrupted DOCX."
        ) from exc

    return len(document.paragraphs)
