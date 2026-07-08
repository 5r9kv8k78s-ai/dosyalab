from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VerificationResult:
    """Return type of `ConversionModule.verify()` — deliberately minimal:
    a converter that wants to report *why* a check failed can still do so
    via `reason`, but nothing here forces every converter to have an
    opinion about failure categories (see the Conversion Platform V2
    architecture report's failure-taxonomy design for that, out of scope
    for this phase).
    """

    ok: bool
    reason: str | None = None


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

    def verify(self, output_path: Path) -> VerificationResult:
        """Confirms `convert()`'s output is actually usable — e.g. that a
        PDF can be reopened, or a DOCX/XLSX container is well-formed. The
        default (`ok=True`, unconditionally) is deliberate: no converter
        implements a real check yet in this phase, and every one of the
        existing 17 tools must keep behaving exactly as before — a
        converter opts into real verification later by overriding this,
        not by this base class assuming one exists.
        """
        return VerificationResult(ok=True)
