import json
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class ExtractPagesConverter(ConversionModule):
    """Extracts selected pages from a PDF into a new PDF, delegating to
    `PdfEngine.extract_pages`.

    `source_path` is a directory containing `source.pdf` and `params.json`
    (holding `pages`) rather than a single file — see
    `submit_extract_pages_job` in app/services/conversion.py.
    """

    slug = "extract-pages"
    input_formats = ("pdf",)
    output_format = "pdf"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        params = json.loads((source_path / "params.json").read_text())
        pdf_path = source_path / "source.pdf"

        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "extracted.pdf"
        return self._engine.extract_pages(pdf_path, output_path, pages=params["pages"])


register_converter(ExtractPagesConverter())
