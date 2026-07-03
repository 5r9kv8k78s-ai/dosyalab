import json
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class RotatePdfConverter(ConversionModule):
    """Rotates one or more pages of a PDF, delegating to
    `PdfEngine.rotate_pdf`.

    `source_path` is a directory containing `source.pdf` and `params.json`
    (holding `rotation` and optional `pages`) rather than a single file —
    see `submit_rotate_pdf_job` in app/services/conversion.py.
    """

    slug = "rotate-pdf"
    input_formats = ("pdf",)
    output_format = "pdf"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        params = json.loads((source_path / "params.json").read_text())
        pdf_path = source_path / "source.pdf"

        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "rotated.pdf"
        return self._engine.rotate_pdf(
            pdf_path, output_path, rotation=params["rotation"], pages=params.get("pages")
        )


register_converter(RotatePdfConverter())
