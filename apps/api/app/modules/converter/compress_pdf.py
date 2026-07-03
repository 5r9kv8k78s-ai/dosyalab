from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class CompressPdfConverter(ConversionModule):
    """Recompresses a PDF to reduce file size, delegating to
    `PdfEngine.compress_pdf`.
    """

    slug = "compress-pdf"
    input_formats = ("pdf",)
    output_format = "pdf"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "compressed.pdf"
        return self._engine.compress_pdf(source_path, output_path)


register_converter(CompressPdfConverter())
