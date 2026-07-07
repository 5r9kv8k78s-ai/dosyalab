from pathlib import Path

import fitz
import pytest

import app.modules.converter.docx_to_pdf as docx_to_pdf_module
from app.modules.converter import get_converter
from app.modules.converter.docx_to_pdf import DocxToPdfConverter


def test_docx_to_pdf_is_registered_automatically() -> None:
    assert isinstance(get_converter("docx-to-pdf"), DocxToPdfConverter)


class _FakeFailedPisaStatus:
    """Stands in for xhtml2pdf's real render-status object — its `log`
    entries carry a message string and an HTML source fragment that can
    quote the user's actual document text (see xhtml2pdf's pisaContext.
    error/warning), which must never reach a log line."""

    err = 2
    warn = 1
    log = [
        ("error", 10, "secret-message-one", "secret-fragment-one"),
        ("error", 25, "secret-message-two", "secret-fragment-two"),
        ("warning", 5, "secret-warning-message", "secret-warning-fragment"),
    ]


def test_docx_to_pdf_render_failure_logs_line_numbers_never_content(
    sample_docx_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    monkeypatch.setattr(
        docx_to_pdf_module.pisa, "CreatePDF", lambda *args, **kwargs: _FakeFailedPisaStatus()
    )

    with caplog.at_level("WARNING", logger="app.modules.converter.docx_to_pdf"):
        with pytest.raises(RuntimeError):
            DocxToPdfConverter().convert(sample_docx_path, tmp_path)

    record = next(r for r in caplog.records if r.msg == "docx_to_pdf.render_errors")
    assert record.error_count == 2
    assert record.warning_count == 1
    assert record.error_line_numbers == [10, 25]

    rendered = " ".join(
        f"{r.getMessage()} {' '.join(str(v) for v in vars(r).values())}" for r in caplog.records
    )
    assert "secret-message" not in rendered
    assert "secret-fragment" not in rendered
    assert "secret-warning" not in rendered


def test_convert_preserves_text_turkish_characters_and_images(
    sample_docx_path: Path, tmp_path: Path
) -> None:
    """Validates the real fixture (a Turkish-language conference program,
    headings/paragraphs/tables/an embedded image) converts with fidelity.

    Turkish characters are checked explicitly because xhtml2pdf's default
    font (standard PDF Helvetica, WinAnsiEncoding) doesn't cover them —
    verified empirically: "İşlemini" rendered as "Ilemini" until the bundled
    Vera TTF was registered as the Helvetica/Times replacement in
    docx_to_pdf.py. This test would catch a regression of that fix.
    """
    output_path = DocxToPdfConverter().convert(sample_docx_path, tmp_path)

    assert output_path.exists()
    assert output_path.suffix == ".pdf"

    pdf = fitz.open(output_path)
    try:
        assert pdf.page_count >= 1

        full_text = "".join(page.get_text() for page in pdf)
        assert "PROCON TRABZON" in full_text
        assert "GENEL BİLGİLER" in full_text  # İ

        for turkish_char in ("ş", "ı", "İ", "ğ", "ü", "ö", "ç"):
            assert turkish_char in full_text, f"expected {turkish_char!r} to survive conversion"

        total_images = sum(len(page.get_images()) for page in pdf)
        assert total_images >= 1
    finally:
        pdf.close()
