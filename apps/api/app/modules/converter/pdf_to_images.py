import json
import shutil
import zipfile
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class PdfToImagesConverter(ConversionModule):
    """Rasterizes every page of a PDF into images, delivered as a single
    zip. Delegates to `PdfEngine.pdf_to_images`.

    The shared job/download pipeline serves one file per job, so the
    resulting page images are zipped into a single archive before being
    returned — the same approach `SplitPdfConverter` uses.

    `source_path` is a directory containing `source.pdf` and `params.json`
    (holding `image_format` and `dpi`) rather than a single file — see
    `submit_pdf_to_images_job` in app/services/conversion.py.
    """

    slug = "pdf-to-images"
    input_formats = ("pdf",)
    output_format = "zip"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        params = json.loads((source_path / "params.json").read_text())
        pdf_path = source_path / "source.pdf"

        destination_dir.mkdir(parents=True, exist_ok=True)
        images_dir = destination_dir / "pages"
        try:
            image_paths = self._engine.pdf_to_images(
                pdf_path,
                images_dir,
                image_format=params["image_format"],
                dpi=params["dpi"],
            )

            zip_path = destination_dir / "pages.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for image_path in image_paths:
                    archive.write(image_path, arcname=image_path.name)
        finally:
            shutil.rmtree(images_dir, ignore_errors=True)

        return zip_path


register_converter(PdfToImagesConverter())
