import json
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class ReorderPagesConverter(ConversionModule):
    """Reorders every page of a PDF, delegating to `PdfEngine.reorder_pages`.

    `source_path` is a directory containing `source.pdf` and `params.json`
    (holding `order`) rather than a single file — see
    `submit_reorder_pages_job` in app/services/conversion.py.
    """

    slug = "reorder-pages"
    input_formats = ("pdf",)
    output_format = "pdf"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        params = json.loads((source_path / "params.json").read_text())
        pdf_path = source_path / "source.pdf"

        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "reordered.pdf"
        return self._engine.reorder_pages(pdf_path, output_path, order=params["order"])


register_converter(ReorderPagesConverter())
