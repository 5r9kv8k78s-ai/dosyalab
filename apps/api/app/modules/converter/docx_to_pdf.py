import logging
from pathlib import Path

import mammoth
import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa

from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter

logger = logging.getLogger(__name__)

_FONTS_REGISTERED = False


def _register_unicode_fonts() -> None:
    """Register a Unicode-capable TTF font and make it xhtml2pdf's default.

    xhtml2pdf renders text with the standard PDF "Helvetica" font unless a
    font-family is explicitly set in the source HTML, and mammoth's HTML
    output doesn't set one. Standard PDF fonts use WinAnsiEncoding, which
    doesn't cover Turkish characters (ş, ı, İ, ğ) — verified empirically:
    text like "İşlemini" rendered as "Ilemini" even after registering a TTF
    with full glyph coverage as a *named* font, because nothing referenced
    that name. Re-registering "Helvetica"/"Times New Roman" as aliases for
    the bundled Unicode font (Vera, shipped with reportlab — no extra
    dependency) fixes this at the source, regardless of what font-family
    the HTML does or doesn't specify.
    """
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    fonts_dir = Path(reportlab.__file__).parent / "fonts"
    pdfmetrics.registerFont(TTFont("Vera", fonts_dir / "Vera.ttf"))
    pdfmetrics.registerFont(TTFont("VeraBd", fonts_dir / "VeraBd.ttf"))
    pdfmetrics.registerFont(TTFont("VeraIt", fonts_dir / "VeraIt.ttf"))
    pdfmetrics.registerFont(TTFont("VeraBI", fonts_dir / "VeraBI.ttf"))

    for family in ("Vera", "Helvetica", "Times New Roman"):
        pdfmetrics.registerFontFamily(
            family, normal="Vera", bold="VeraBd", italic="VeraIt", boldItalic="VeraBI"
        )

    _FONTS_REGISTERED = True


class DocxToPdfConverter(ConversionModule):
    """Converts DOCX documents to PDF via an HTML intermediate: mammoth
    extracts the document to HTML (preserving headings, paragraphs, images,
    and basic table structure), and xhtml2pdf renders that HTML to PDF.

    No system dependency (e.g. LibreOffice) is required — both libraries are
    pure Python plus reportlab, which is itself pure Python.
    """

    slug = "docx-to-pdf"
    input_formats = ("docx",)
    output_format = "pdf"

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.pdf"

        _register_unicode_fonts()

        logger.info("docx_to_pdf.convert.start", extra={"source": str(source_path)})
        with open(source_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
        html = f"<html><body>{result.value}</body></html>"

        with open(output_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(f"xhtml2pdf reported {pisa_status.err} error(s) during rendering")

        logger.info("docx_to_pdf.convert.done", extra={"output": str(output_path)})
        return output_path


register_converter(DocxToPdfConverter())
