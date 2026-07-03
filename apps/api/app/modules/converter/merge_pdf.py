import uuid
from pathlib import Path

from app.converters.pdf_engine import PdfEngine
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter


class MergePdfConverter(ConversionModule):
    """Merges an ordered directory of PDFs into a single PDF.

    Delegates the actual merge to `PdfEngine.merge_pdf` (the shared PDF
    manipulation engine) — this class only adapts that call to the
    `ConversionModule` contract. Like `ImagesToPdfConverter`, `source_path`
    is a directory of ordered files rather than a single file; see
    `submit_merge_pdf_job` in app/services/conversion.py for how upload
    order is preserved via zero-padded filename prefixes.
    """

    slug = "merge-pdf"
    input_formats = ("pdf",)
    output_format = "pdf"

    def __init__(self) -> None:
        self._engine = PdfEngine()

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        input_paths = sorted(p for p in source_path.iterdir() if p.is_file())
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{uuid.uuid4().hex}.pdf"
        return self._engine.merge_pdf(input_paths, output_path)


register_converter(MergePdfConverter())
