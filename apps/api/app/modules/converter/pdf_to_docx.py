import logging
import threading
from contextlib import contextmanager
from pathlib import Path

import fitz
from pdf2docx import Converter
from pdf2docx.image.ImagesExtractor import ImagesExtractor

from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter

logger = logging.getLogger(__name__)

# The only two colorspaces PyMuPDF's PNG writer (`fz_write_pixmap_as_png`)
# accepts — anything else must be converted to RGB before serialization.
_PNG_SAFE_COLORSPACE_NAMES = {"DeviceGray", "DeviceRGB"}


def _normalize_pixmap_for_png(pix: fitz.Pixmap) -> fitz.Pixmap:
    """Returns a Pixmap PyMuPDF can serialize as PNG (grayscale or RGB,
    alpha preserved either way).

    pdf2docx==0.5.8's own CMYK handling (`ImagesExtractor._recover_pixmap`)
    only recognizes colorspaces whose *name* literally contains "CMYK" —
    real-world PDFs can embed images in other non-gray/non-RGB colorspaces
    (Separation, DeviceN, Indexed-with-a-non-RGB-base, Lab, differently
    named ICC profiles, ...) that slip past that check untouched. Those
    then reach `Pixmap.tobytes()` (PNG by default) unconverted and raise —
    this is the exact boundary the production traceback for tool_slug
    "pdf-to-docx" showed (`ImagesExtractor._to_raw_dict` -> `image.tobytes`
    -> `fz_write_pixmap_as_png`), during pdf2docx's `parse_document()` step,
    which (unlike its per-page `parse_pages()` step) has no error-recovery
    wrapper of its own — the exception reaches this module uncaught.

    A `colorspace` of `None` (e.g. a stencil-mask-only pixmap) is left
    alone — there's no color data to normalize, and pdf2docx never routes
    those through this same serialization path in the first place.
    """
    colorspace = pix.colorspace
    if colorspace is None or colorspace.name in _PNG_SAFE_COLORSPACE_NAMES:
        return pix
    return fitz.Pixmap(fitz.csRGB, pix)


_original_to_raw_dict = ImagesExtractor._to_raw_dict
_patch_lock = threading.Lock()
_patch_refcount = 0


def _to_raw_dict_with_png_safe_colorspace(image: fitz.Pixmap, bbox: fitz.Rect) -> dict:
    return _original_to_raw_dict(_normalize_pixmap_for_png(image), bbox)


@contextmanager
def _png_safe_image_serialization():
    """Scoped patch of `ImagesExtractor._to_raw_dict` for the duration of a
    `Converter.convert()` call — see `_normalize_pixmap_for_png` for why.

    Reference-counted rather than a naive "patch then restore in finally":
    conversions run concurrently across OS threads (`asyncio.to_thread` in
    `app/services/conversion.py`), all sharing this same *process-wide*
    pdf2docx class. A naive restore would let one conversion's cleanup rip
    the patch out from under a different conversion still mid-flight in
    another thread — this keeps it installed for as long as at least one
    conversion is using it, and only ever removes it (rather than leaving
    a permanent, unconditional patch) once none are.
    """
    global _patch_refcount
    with _patch_lock:
        if _patch_refcount == 0:
            ImagesExtractor._to_raw_dict = staticmethod(_to_raw_dict_with_png_safe_colorspace)
        _patch_refcount += 1
    try:
        yield
    finally:
        with _patch_lock:
            _patch_refcount -= 1
            if _patch_refcount == 0:
                ImagesExtractor._to_raw_dict = staticmethod(_original_to_raw_dict)


class PdfToDocxConverter(ConversionModule):
    """Converts PDF documents to DOCX, preserving layout, headings, images,
    and tables via pdf2docx's default layout analysis.

    pdf2docx's `Converter.parse()` does not expose a public per-page progress
    callback: calling it repeatedly with different page ranges resets the
    converter's internal page state on each call rather than accumulating
    results (verified empirically — only the last-parsed page survived in the
    output document). So this module performs the conversion as a single
    blocking `convert()` call; callers that need progress feedback during
    that call approximate it externally (see `app/services/conversion.py`).
    """

    slug = "pdf-to-docx"
    input_formats = ("pdf",)
    output_format = "docx"

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.docx"

        logger.info("pdf_to_docx.convert.start", extra={"source": str(source_path)})
        converter = Converter(str(source_path))
        try:
            with _png_safe_image_serialization():
                converter.convert(str(output_path))
        finally:
            converter.close()
        logger.info("pdf_to_docx.convert.done", extra={"output": str(output_path)})

        return output_path


register_converter(PdfToDocxConverter())
