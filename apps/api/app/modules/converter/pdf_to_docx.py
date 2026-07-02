import logging
from pathlib import Path

from pdf2docx import Converter

from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter

logger = logging.getLogger(__name__)


class PdfToDocxConverter(ConversionModule):
    """Converts PDF documents to DOCX, preserving layout, headings, images,
    and tables via pdf2docx's default layout analysis.

    pdf2docx's `Converter.parse()` does not expose a public per-page progress
    callback: calling it repeatedly with different page ranges resets the
    converter's internal page state on each call rather than accumulating
    results (verified empirically — only the last-parsed page survived in the
    output document). So this module performs the conversion as a single
    blocking `convert()` call; callers that need progress feedback during
    that call approximate it externally (see `app/services/conversion.py`).
    """

    slug = "pdf-to-docx"
    input_formats = ("pdf",)
    output_format = "docx"

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.docx"

        logger.info("pdf_to_docx.convert.start", extra={"source": str(source_path)})
        converter = Converter(str(source_path))
        try:
            converter.convert(str(output_path))
        finally:
            converter.close()
        logger.info("pdf_to_docx.convert.done", extra={"output": str(output_path)})

        return output_path


register_converter(PdfToDocxConverter())
