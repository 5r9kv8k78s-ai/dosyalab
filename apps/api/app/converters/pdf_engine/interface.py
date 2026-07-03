from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path


class PdfEngineInterface(ABC):
    """Contract for PDF-manipulation engines.

    Callers should depend on this abstraction rather than the concrete
    `PdfEngine` implementation, so alternative engines can be substituted
    without changing call sites (Dependency Inversion Principle).

    Page numbers throughout are 0-indexed, matching PyMuPDF convention.
    """

    @abstractmethod
    def merge_pdf(self, input_paths: Sequence[Path], output_path: Path) -> Path: ...

    @abstractmethod
    def split_pdf(
        self, input_path: Path, output_dir: Path, pages_per_file: int = 1
    ) -> list[Path]: ...

    @abstractmethod
    def compress_pdf(self, input_path: Path, output_path: Path) -> Path: ...

    @abstractmethod
    def rotate_pdf(
        self,
        input_path: Path,
        output_path: Path,
        rotation: int,
        pages: Sequence[int] | None = None,
    ) -> Path: ...

    @abstractmethod
    def delete_pages(self, input_path: Path, output_path: Path, pages: Sequence[int]) -> Path: ...

    @abstractmethod
    def extract_pages(self, input_path: Path, output_path: Path, pages: Sequence[int]) -> Path: ...

    @abstractmethod
    def reorder_pages(self, input_path: Path, output_path: Path, order: Sequence[int]) -> Path: ...

    @abstractmethod
    def watermark_pdf(
        self,
        input_path: Path,
        output_path: Path,
        text: str,
        *,
        opacity: float = 0.3,
        font_size: int = 40,
        rotation: float = 45.0,
    ) -> Path: ...

    @abstractmethod
    def protect_pdf(
        self,
        input_path: Path,
        output_path: Path,
        user_password: str,
        owner_password: str | None = None,
    ) -> Path: ...

    @abstractmethod
    def unlock_pdf(self, input_path: Path, output_path: Path, password: str) -> Path: ...

    @abstractmethod
    def pdf_to_images(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        image_format: str = "png",
        dpi: int = 150,
    ) -> list[Path]: ...

    @abstractmethod
    def extract_images(self, input_path: Path, output_dir: Path) -> list[Path]: ...

    @abstractmethod
    def extract_text(self, input_path: Path, pages: Sequence[int] | None = None) -> str: ...
