from pathlib import Path

from PIL import Image, UnidentifiedImageError

# Re-exported rather than duplicated: this function has no PDF-specific
# logic (just filename sanitization), so it's shared as-is across converters.
from app.services.pdf_validation import secure_filename  # noqa: F401

_ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


class ImageValidationError(Exception):
    """Raised when an uploaded file fails image validation.

    `status_code` lets the endpoint translate this straight into an HTTP
    response without a separate mapping table. `error_code` is a small,
    stable category (see app/services/operations_events.py) for the
    privacy-safe operations event, never the raw `message` text.
    """

    def __init__(self, message: str, status_code: int = 400, error_code: str = "validation_failed"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def validate_image_extension(filename: str) -> None:
    if not filename.lower().endswith(_ALLOWED_EXTENSIONS):
        raise ImageValidationError(
            "Only JPG, JPEG, PNG, and WEBP files are accepted.", error_code="invalid_file_type"
        )


def validate_image_size(size_bytes: int, max_size_mb: int) -> None:
    if size_bytes == 0:
        raise ImageValidationError("The uploaded file is empty.", error_code="invalid_file_type")
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ImageValidationError(
            f"File exceeds the {max_size_mb}MB size limit.",
            status_code=413,
            error_code="file_too_large",
        )


def inspect_image(path: Path) -> tuple[int, int]:
    """Open the image to confirm it is readable and not corrupted.

    Returns (width, height) on success; raises ImageValidationError for
    unreadable or corrupted files.
    """
    try:
        with Image.open(path) as image:
            image.load()
            return image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError(
            "The uploaded file is not a valid or is a corrupted image."
        ) from exc
