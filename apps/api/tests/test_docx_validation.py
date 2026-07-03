from pathlib import Path

import pytest

from app.services.docx_validation import (
    DocxValidationError,
    inspect_docx,
    secure_filename,
    validate_docx_extension,
    validate_docx_size,
)


def test_secure_filename_strips_path_traversal() -> None:
    assert secure_filename("../../etc/passwd.docx") == "passwd.docx"


def test_validate_docx_extension_accepts_docx() -> None:
    validate_docx_extension("report.docx")


def test_validate_docx_extension_rejects_other_types() -> None:
    with pytest.raises(DocxValidationError):
        validate_docx_extension("report.pdf")


def test_validate_docx_size_rejects_empty_file() -> None:
    with pytest.raises(DocxValidationError):
        validate_docx_size(0, max_size_mb=25)


def test_validate_docx_size_rejects_oversized_file() -> None:
    with pytest.raises(DocxValidationError) as exc_info:
        validate_docx_size(200 * 1024 * 1024, max_size_mb=100)
    assert exc_info.value.status_code == 413


def test_validate_docx_size_accepts_within_limit() -> None:
    validate_docx_size(1024, max_size_mb=100)


def test_inspect_docx_accepts_real_sample(sample_docx_path: Path) -> None:
    paragraph_count = inspect_docx(sample_docx_path)
    assert paragraph_count == 131


def test_inspect_docx_rejects_corrupted_docx(tmp_path: Path, corrupted_docx_bytes: bytes) -> None:
    path = tmp_path / "corrupted.docx"
    path.write_bytes(corrupted_docx_bytes)
    with pytest.raises(DocxValidationError, match="corrupted"):
        inspect_docx(path)


def test_inspect_docx_rejects_encrypted_docx(tmp_path: Path, encrypted_docx_bytes: bytes) -> None:
    path = tmp_path / "encrypted.docx"
    path.write_bytes(encrypted_docx_bytes)
    with pytest.raises(DocxValidationError, match="Encrypted"):
        inspect_docx(path)
