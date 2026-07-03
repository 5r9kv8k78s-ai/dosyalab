from pathlib import Path

import fitz

from app.modules.converter import get_converter
from app.modules.converter.docx_to_pdf import DocxToPdfConverter


def test_docx_to_pdf_is_registered_automatically() -> None:
    assert isinstance(get_converter("docx-to-pdf"), DocxToPdfConverter)


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
