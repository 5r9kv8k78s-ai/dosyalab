import json
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class ProtectPdfConverter(ConversionModule):
    """Encrypts a PDF with a password, delegating to `PdfEngine.protect_pdf`.

    `source_path` is a directory containing `source.pdf` and `params.json`
    (holding `user_password` and optional `owner_password`) rather than a
    single file — see `submit_protect_pdf_job` in
    app/services/conversion.py.
    """

    slug = "protect-pdf"
    input_formats = ("pdf",)
    output_format = "pdf"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        params = json.loads((source_path / "params.json").read_text())
        pdf_path = source_path / "source.pdf"

        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "protected.pdf"
        return self._engine.protect_pdf(
            pdf_path,
            output_path,
            params["user_password"],
            owner_password=params.get("owner_password"),
        )


register_converter(ProtectPdfConverter())
