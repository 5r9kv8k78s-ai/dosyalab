class PdfEngineError(Exception):
    """Base exception for all PdfEngine operations."""


class CorruptPdfError(PdfEngineError):
    """Raised when a PDF file cannot be opened or parsed."""


class InvalidPageRangeError(PdfEngineError):
    """Raised when requested page numbers are missing, out of bounds, or malformed."""


class PdfPasswordError(PdfEngineError):
    """Raised when a password-protected PDF cannot be accessed with the given password."""
