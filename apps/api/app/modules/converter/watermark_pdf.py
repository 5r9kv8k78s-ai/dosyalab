import json
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class WatermarkPdfConverter(ConversionModule):
    """Stamps a text watermark across every page of a PDF, delegating to
    `PdfEngine.watermark_pdf`.

    `source_path` is a directory containing `source.pdf` and `params.json`
    (holding `text`, `opacity`, `font_size`, `rotation`) rather than a
    single file — see `submit_watermark_pdf_job` in
    app/services/conversion.py.
    """

    slug = "watermark-pdf"
    input_formats = ("pdf",)
    output_format = "pdf"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        params = json.loads((source_path / "params.json").read_text())
        pdf_path = source_path / "source.pdf"

        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "watermarked.pdf"
        return self._engine.watermark_pdf(
            pdf_path,
            output_path,
            params["text"],
            opacity=params["opacity"],
            font_size=params["font_size"],
            rotation=params["rotation"],
        )


register_converter(WatermarkPdfConverter())
