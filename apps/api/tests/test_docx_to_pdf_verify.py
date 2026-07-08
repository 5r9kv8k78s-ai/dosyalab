"""`DocxToPdfConverter.verify()` (see app/modules/converter/docx_to_pdf.py) —
V2-1's first real output verifier. Independent of xhtml2pdf's own
`pisa_status.err` check inside `convert()`: this re-opens the actual bytes
written to disk with a different library (PyMuPDF), as a defense-in-depth
net against a "successful" render that produced a corrupt or empty PDF.
"""

from pathlib import Path

from app.modules.converter.base import VerificationResult
from app.modules.converter.docx_to_pdf import DocxToPdfConverter


def test_verify_ok_true_on_a_real_successful_conversion(
    sample_docx_path: Path, tmp_path: Path
) -> None:
    output_path = DocxToPdfConverter().convert(sample_docx_path, tmp_path)

    result = DocxToPdfConverter().verify(output_path)

    assert result == VerificationResult(ok=True, reason=None)


def test_verify_rejects_a_missing_output_file(tmp_path: Path) -> None:
    result = DocxToPdfConverter().verify(tmp_path / "never-written.pdf")

    assert result.ok is False
    assert result.reason == "output_missing"


def test_verify_rejects_bytes_that_are_not_a_pdf_at_all(tmp_path: Path) -> None:
    fake_output = tmp_path / "not-a-pdf.pdf"
    fake_output.write_bytes(b"this is not a pdf")

    result = DocxToPdfConverter().verify(fake_output)

    assert result.ok is False
    assert result.reason == "invalid_pdf"


def test_verify_rejects_a_structurally_valid_but_zero_page_pdf(tmp_path: Path) -> None:
    # PyMuPDF itself refuses to *save* a zero-page document (`ValueError:
    # cannot save with zero pages`), so this scenario can't be produced via
    # fitz's own API — a minimal, hand-written, spec-valid zero-page PDF
    # (empty /Pages /Kids, /Count 0) is what a corrupted/truncated render
    # that never wrote any page content would look like on disk instead.
    # Verified PyMuPDF opens this without error and reports page_count == 0.
    empty_output = tmp_path / "zero-pages.pdf"
    empty_output.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n"
        b"%%EOF\n"
    )

    result = DocxToPdfConverter().verify(empty_output)

    assert result.ok is False
    assert result.reason == "zero_pages"
