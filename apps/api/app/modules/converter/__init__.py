"""
Document conversion module registry.

Future conversion modules (e.g. docx-to-pdf, image-to-pdf, csv-to-xlsx) register
themselves here via `register_converter`, keeping `app/api` free of per-format
logic. See `base.py` for the interface new modules must implement.
"""

# Importing a module here triggers its module-level `register_converter(...)`
# call, making it available in the registry as soon as this package is
# imported. New conversion modules join this list — no other wiring needed.
from app.modules.converter import compress_pdf as _compress_pdf  # noqa: E402,F401
from app.modules.converter import docx_to_pdf as _docx_to_pdf  # noqa: E402,F401
from app.modules.converter import images_to_pdf as _images_to_pdf  # noqa: E402,F401
from app.modules.converter import merge_pdf as _merge_pdf  # noqa: E402,F401
from app.modules.converter import pdf_to_docx as _pdf_to_docx  # noqa: E402,F401
from app.modules.converter import pdf_to_xlsx as _pdf_to_xlsx  # noqa: E402,F401
from app.modules.converter import rotate_pdf as _rotate_pdf  # noqa: E402,F401
from app.modules.converter import split_pdf as _split_pdf  # noqa: E402,F401
from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import get_converter, list_converters, register_converter

__all__ = [
    "ConversionModule",
    "register_converter",
    "get_converter",
    "list_converters",
]
