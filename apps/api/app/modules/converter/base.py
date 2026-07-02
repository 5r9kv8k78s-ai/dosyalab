from abc import ABC, abstractmethod
from pathlib import Path


class ConversionModule(ABC):
    """Base class every document conversion module must implement.

    Subclass this in a new module under `app/modules/converter/` and register
    an instance with `register_converter` to plug it into the upload/convert
    pipeline without touching API or routing code.
    """

    #: Unique identifier used in API requests, e.g. "docx-to-pdf".
    slug: str

    #: File extensions this module accepts, without the leading dot.
    input_formats: tuple[str, ...]

    #: File extension this module produces, without the leading dot.
    output_format: str

    @abstractmethod
    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        """Convert `source_path` and return the path to the resulting file."""
        raise NotImplementedError
