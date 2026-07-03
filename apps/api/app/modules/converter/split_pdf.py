import json
import shutil
import zipfile
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class SplitPdfConverter(ConversionModule):
    """Splits a PDF into multiple smaller PDFs, delivered as a single zip.

    Delegates the actual split to `PdfEngine.split_pdf`. The shared job/
    download pipeline serves one file per job, so the resulting parts are
    zipped into a single archive before being returned.

    `source_path` is a directory containing `source.pdf` and `params.json`
    (holding `pages_per_file`) rather than a single file — see
    `submit_split_pdf_job` in app/services/conversion.py.
    """

    slug = "split-pdf"
    input_formats = ("pdf",)
    output_format = "zip"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        params = json.loads((source_path / "params.json").read_text())
        pdf_path = source_path / "source.pdf"

        destination_dir.mkdir(parents=True, exist_ok=True)
        parts_dir = destination_dir / "split_parts"
        try:
            part_paths = self._engine.split_pdf(
                pdf_path, parts_dir, pages_per_file=params["pages_per_file"]
            )

            zip_path = destination_dir / "split.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for part_path in part_paths:
                    archive.write(part_path, arcname=part_path.name)
        finally:
            shutil.rmtree(parts_dir, ignore_errors=True)

        return zip_path


register_converter(SplitPdfConverter())
