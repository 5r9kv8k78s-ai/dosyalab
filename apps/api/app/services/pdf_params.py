from app.services.pdf_validation import PdfValidationError


def parse_page_list(raw: str | None, *, field_name: str = "pages") -> list[int] | None:
    """Parses a comma-separated, 1-indexed page list from a form field into
    a 0-indexed list for PdfEngine. Returns None if `raw` is empty/None,
    signalling "no explicit selection" to callers that treat that as "all
    pages".
    """
    if raw is None or not raw.strip():
        return None
    try:
        one_indexed = [int(piece.strip()) for piece in raw.split(",") if piece.strip()]
    except ValueError as exc:
        raise PdfValidationError(
            f"{field_name} must be a comma-separated list of page numbers."
        ) from exc
    if not one_indexed:
        return None
    if any(page < 1 for page in one_indexed):
        raise PdfValidationError(f"{field_name} must use 1-based page numbers.")
    return [page - 1 for page in one_indexed]


def validate_pages_in_range(
    pages: list[int], page_count: int, *, field_name: str = "pages"
) -> None:
    for zero_indexed in pages:
        if zero_indexed < 0 or zero_indexed >= page_count:
            raise PdfValidationError(
                f"{field_name} references page {zero_indexed + 1}, out of range for a "
                f"{page_count}-page document."
            )
