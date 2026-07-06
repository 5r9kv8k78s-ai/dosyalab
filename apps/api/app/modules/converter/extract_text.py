import json
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter

# PdfEngine.extract_text only reads a PDF's embedded text layer (PyMuPDF's
# get_text()) — a scanned/image-only PDF has none, and previously came back
# as a silently empty .txt file with no indication why. This isn't OCR (out
# of scope); it's just telling the user what actually happened instead of
# handing them a blank download.
_NO_TEXT_FOUND_MESSAGE = (
    "No text could be extracted from this PDF. It may be a scanned document "
    "or an image-only PDF with no embedded text layer."
)


class ExtractTextConverter(ConversionModule):
    """Extracts text content from a PDF into a .txt file, delegating to
    `PdfEngine.extract_text`.

    `source_path` is a directory containing `source.pdf` and `params.json`
    (holding an optional `pages`) rather than a single file — see
    `submit_extract_text_job` in app/services/conversion.py.
    """

    slug = "extract-text"
    input_formats = ("pdf",)
    output_format = "txt"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        params = json.loads((source_path / "params.json").read_text())
        pdf_path = source_path / "source.pdf"

        text = self._engine.extract_text(pdf_path, pages=params.get("pages"))

        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "extracted.txt"
        output_path.write_text(text if text.strip() else _NO_TEXT_FOUND_MESSAGE, encoding="utf-8")
        return output_path


register_converter(ExtractTextConverter())
