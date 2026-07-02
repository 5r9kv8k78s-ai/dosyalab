from pathlib import Path

import pytest

from app.services.pdf_validation import (
    PdfValidationError,
    inspect_pdf,
    secure_filename,
    validate_pdf_extension,
    validate_pdf_size,
)


def test_secure_filename_strips_path_traversal() -> None:
    assert secure_filename("../../etc/passwd.pdf") == "passwd.pdf"


def test_secure_filename_strips_windows_style_traversal() -> None:
    assert secure_filename("..\\..\\windows\\evil.pdf") == "windows_evil.pdf"


def test_secure_filename_folds_unicode_and_unsafe_chars() -> None:
    result = secure_filename("Fatura Örneği (2026)!.pdf")
    assert result.endswith(".pdf")
    assert " " not in result
    assert "(" not in result
    assert ")" not in result


def test_secure_filename_handles_missing_name() -> None:
    assert secure_filename("") == "document"
    assert secure_filename(None) == "document"


def test_validate_pdf_extension_accepts_pdf() -> None:
    validate_pdf_extension("invoice.pdf")


def test_validate_pdf_extension_rejects_other_types() -> None:
    with pytest.raises(PdfValidationError):
        validate_pdf_extension("invoice.docx")


def test_validate_pdf_size_rejects_empty_file() -> None:
    with pytest.raises(PdfValidationError):
        validate_pdf_size(0, max_size_mb=25)


def test_validate_pdf_size_rejects_oversized_file() -> None:
    with pytest.raises(PdfValidationError) as exc_info:
        validate_pdf_size(200 * 1024 * 1024, max_size_mb=100)
    assert exc_info.value.status_code == 413


def test_validate_pdf_size_accepts_within_limit() -> None:
    validate_pdf_size(1024, max_size_mb=100)


def test_inspect_pdf_accepts_real_sample(sample_pdf_path: Path) -> None:
    page_count = inspect_pdf(sample_pdf_path)
    assert page_count == 6


def test_inspect_pdf_rejects_corrupted_pdf(tmp_path: Path, corrupted_pdf_bytes: bytes) -> None:
    path = tmp_path / "corrupted.pdf"
    path.write_bytes(corrupted_pdf_bytes)
    with pytest.raises(PdfValidationError, match="corrupted"):
        inspect_pdf(path)


def test_inspect_pdf_rejects_encrypted_pdf(tmp_path: Path, encrypted_pdf_bytes: bytes) -> None:
    path = tmp_path / "encrypted.pdf"
    path.write_bytes(encrypted_pdf_bytes)
    with pytest.raises(PdfValidationError, match="Encrypted"):
        inspect_pdf(path)
