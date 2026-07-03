import shutil
import zipfile
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class ExtractImagesConverter(ConversionModule):
    """Extracts every embedded image from a PDF, delivered as a single zip.
    Delegates to `PdfEngine.extract_images`.

    Raises if the PDF has no embedded images, mirroring
    `PdfToXlsxConverter`'s behavior for PDFs with no extractable tables.
    """

    slug = "extract-images"
    input_formats = ("pdf",)
    output_format = "zip"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        destination_dir.mkdir(parents=True, exist_ok=True)
        images_dir = destination_dir / "images"
        try:
            image_paths = self._engine.extract_images(source_path, images_dir)
            if not image_paths:
                raise ValueError("This PDF has no embedded images to extract.")

            zip_path = destination_dir / "images.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for image_path in image_paths:
                    archive.write(image_path, arcname=image_path.name)
        finally:
            shutil.rmtree(images_dir, ignore_errors=True)

        return zip_path


register_converter(ExtractImagesConverter())
