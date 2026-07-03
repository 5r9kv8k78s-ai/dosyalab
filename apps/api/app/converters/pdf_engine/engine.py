from collections.abc import Sequence
from pathlib import Path

import fitz

from app.converters.pdf_engine.exceptions import (
    CorruptPdfError,
    InvalidPageRangeError,
    PdfEngineError,
    PdfPasswordError,
)
from app.converters.pdf_engine.interface import PdfEngineInterface

_SUPPORTED_IMAGE_FORMATS = {"png", "jpg", "jpeg"}


class PdfEngine(PdfEngineInterface):
    """PyMuPDF-backed implementation of `PdfEngineInterface`.

    Stateless: every method opens its own input(s), writes fresh output
    file(s), and closes all documents before returning. Safe to share a
    single instance across requests.
    """

    def merge_pdf(self, input_paths: Sequence[Path], output_path: Path) -> Path:
        if len(input_paths) < 2:
            raise PdfEngineError("merge_pdf requires at least two input PDFs.")

        merged = fitz.open()
        try:
            for input_path in input_paths:
                with self._open(input_path) as doc:
                    merged.insert_pdf(doc)
            self._ensure_parent_dir(output_path)
            merged.save(output_path)
        finally:
            merged.close()
        return output_path

    def split_pdf(self, input_path: Path, output_dir: Path, pages_per_file: int = 1) -> list[Path]:
        if pages_per_file < 1:
            raise PdfEngineError("pages_per_file must be at least 1.")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths: list[Path] = []
        with self._open(input_path) as doc:
            chunk_index = 0
            for start in range(0, doc.page_count, pages_per_file):
                end = min(start + pages_per_file, doc.page_count)
                chunk_index += 1
                chunk = fitz.open()
                try:
                    chunk.insert_pdf(doc, from_page=start, to_page=end - 1)
                    chunk_path = output_dir / f"{input_path.stem}_part{chunk_index}.pdf"
                    chunk.save(chunk_path)
                finally:
                    chunk.close()
                output_paths.append(chunk_path)
        return output_paths

    def compress_pdf(self, input_path: Path, output_path: Path) -> Path:
        with self._open(input_path) as doc:
            self._ensure_parent_dir(output_path)
            doc.save(output_path, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True)
        return output_path

    def rotate_pdf(
        self,
        input_path: Path,
        output_path: Path,
        rotation: int,
        pages: Sequence[int] | None = None,
    ) -> Path:
        if rotation % 90 != 0:
            raise PdfEngineError("rotation must be a multiple of 90 degrees.")

        with self._open(input_path) as doc:
            for page_number in self._resolve_pages(doc.page_count, pages):
                page = doc[page_number]
                page.set_rotation((page.rotation + rotation) % 360)
            self._ensure_parent_dir(output_path)
            doc.save(output_path)
        return output_path

    def delete_pages(self, input_path: Path, output_path: Path, pages: Sequence[int]) -> Path:
        with self._open(input_path) as doc:
            self._validate_pages(doc.page_count, pages)
            unique_pages = set(pages)
            if len(unique_pages) >= doc.page_count:
                raise PdfEngineError("Cannot delete all pages from a PDF.")
            doc.delete_pages(sorted(unique_pages))
            self._ensure_parent_dir(output_path)
            doc.save(output_path)
        return output_path

    def extract_pages(self, input_path: Path, output_path: Path, pages: Sequence[int]) -> Path:
        with self._open(input_path) as doc:
            self._validate_pages(doc.page_count, pages)
            doc.select(list(pages))
            self._ensure_parent_dir(output_path)
            doc.save(output_path)
        return output_path

    def reorder_pages(self, input_path: Path, output_path: Path, order: Sequence[int]) -> Path:
        with self._open(input_path) as doc:
            if len(order) != doc.page_count or set(order) != set(range(doc.page_count)):
                raise InvalidPageRangeError(
                    "order must be a permutation of every page index in the document."
                )
            doc.select(list(order))
            self._ensure_parent_dir(output_path)
            doc.save(output_path)
        return output_path

    def watermark_pdf(
        self,
        input_path: Path,
        output_path: Path,
        text: str,
        *,
        opacity: float = 0.3,
        font_size: int = 40,
        rotation: float = 45.0,
    ) -> Path:
        if not text:
            raise PdfEngineError("Watermark text must not be empty.")

        gray_level = 1 - min(max(opacity, 0.0), 1.0)
        with self._open(input_path) as doc:
            for page in doc:
                rect = page.rect
                center = fitz.Point(rect.width / 2, rect.height / 2)
                text_width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
                origin = (rect.width / 2 - text_width / 2, rect.height / 2)
                page.insert_text(
                    origin,
                    text,
                    fontsize=font_size,
                    fontname="helv",
                    color=(gray_level, gray_level, gray_level),
                    morph=(center, fitz.Matrix(rotation)),
                    overlay=True,
                )
            self._ensure_parent_dir(output_path)
            doc.save(output_path)
        return output_path

    def protect_pdf(
        self,
        input_path: Path,
        output_path: Path,
        user_password: str,
        owner_password: str | None = None,
    ) -> Path:
        if not user_password:
            raise PdfEngineError("A user password is required to protect a PDF.")

        with self._open(input_path) as doc:
            self._ensure_parent_dir(output_path)
            doc.save(
                output_path,
                encryption=fitz.PDF_ENCRYPT_AES_256,
                user_pw=user_password,
                owner_pw=owner_password or user_password,
            )
        return output_path

    def unlock_pdf(self, input_path: Path, output_path: Path, password: str) -> Path:
        doc = self._open_raw(input_path)
        try:
            if doc.is_encrypted and not doc.authenticate(password):
                raise PdfPasswordError("The provided password is incorrect.")
            self._ensure_parent_dir(output_path)
            doc.save(output_path)
        finally:
            doc.close()
        return output_path

    def pdf_to_images(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        image_format: str = "png",
        dpi: int = 150,
    ) -> list[Path]:
        image_format = image_format.lower().lstrip(".")
        if image_format not in _SUPPORTED_IMAGE_FORMATS:
            raise PdfEngineError(f"Unsupported image format: {image_format!r}.")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths: list[Path] = []
        with self._open(input_path) as doc:
            digits = len(str(doc.page_count))
            for page_number in range(doc.page_count):
                pixmap = doc[page_number].get_pixmap(dpi=dpi)
                image_path = (
                    output_dir
                    / f"{input_path.stem}_page{page_number + 1:0{digits}d}.{image_format}"
                )
                pixmap.save(image_path)
                output_paths.append(image_path)
        return output_paths

    def extract_images(self, input_path: Path, output_dir: Path) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths: list[Path] = []
        with self._open(input_path) as doc:
            seen_xrefs: set[int] = set()
            image_index = 0
            for page_number in range(doc.page_count):
                for image_info in doc.get_page_images(page_number):
                    xref = image_info[0]
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    image_index += 1
                    extracted = doc.extract_image(xref)
                    image_path = (
                        output_dir / f"{input_path.stem}_image{image_index}.{extracted['ext']}"
                    )
                    image_path.write_bytes(extracted["image"])
                    output_paths.append(image_path)
        return output_paths

    def extract_text(self, input_path: Path, pages: Sequence[int] | None = None) -> str:
        with self._open(input_path) as doc:
            page_numbers = self._resolve_pages(doc.page_count, pages)
            return "\n".join(doc[page_number].get_text() for page_number in page_numbers)

    def _open_raw(self, path: Path) -> fitz.Document:
        try:
            return fitz.open(path)
        except Exception as exc:
            raise CorruptPdfError(f"Could not open '{path.name}' as a PDF.") from exc

    def _open(self, path: Path) -> fitz.Document:
        doc = self._open_raw(path)
        if doc.is_encrypted:
            doc.close()
            raise PdfPasswordError(
                f"'{path.name}' is password-protected. Unlock it first with unlock_pdf()."
            )
        return doc

    def _resolve_pages(self, page_count: int, pages: Sequence[int] | None) -> list[int]:
        if pages is None:
            return list(range(page_count))
        self._validate_pages(page_count, pages)
        return list(pages)

    def _validate_pages(self, page_count: int, pages: Sequence[int]) -> None:
        if not pages:
            raise InvalidPageRangeError("At least one page must be specified.")
        for page_number in pages:
            if page_number < 0 or page_number >= page_count:
                raise InvalidPageRangeError(
                    f"Page {page_number} is out of range for a {page_count}-page document."
                )

    def _ensure_parent_dir(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
