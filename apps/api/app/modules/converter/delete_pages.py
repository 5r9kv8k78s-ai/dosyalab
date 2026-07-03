import json
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class DeletePagesConverter(ConversionModule):
    """Deletes selected pages from a PDF, delegating to
    `PdfEngine.delete_pages`.

    `source_path` is a directory containing `source.pdf` and `params.json`
    (holding `pages`) rather than a single file — see
    `submit_delete_pages_job` in app/services/conversion.py.
    """

    slug = "delete-pages"
    input_formats = ("pdf",)
    output_format = "pdf"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        params = json.loads((source_path / "params.json").read_text())
        pdf_path = source_path / "source.pdf"

        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "deleted.pdf"
        return self._engine.delete_pages(pdf_path, output_path, pages=params["pages"])


register_converter(DeletePagesConverter())
