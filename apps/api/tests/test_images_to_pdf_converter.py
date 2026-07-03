from pathlib import Path

import fitz
import pytest

from app.modules.converter import get_converter
from app.modules.converter.images_to_pdf import ImagesToPdfConverter


def test_images_to_pdf_is_registered_automatically() -> None:
    assert isinstance(get_converter("images-to-pdf"), ImagesToPdfConverter)


def test_convert_combines_mixed_format_images_in_order(
    sample_jpg_bytes: bytes,
    sample_png_bytes: bytes,
    sample_webp_bytes: bytes,
    tmp_path: Path,
) -> None:
    """Simulates what submit_images_to_pdf_job produces: a directory of
    zero-padded, order-prefixed image files (mixed JPG/PNG/WEBP, all real —
    derived from the same real DosyaLab brand asset in different formats,
    see conftest.py).
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "0000_a.jpg").write_bytes(sample_jpg_bytes)
    (source_dir / "0001_b.png").write_bytes(sample_png_bytes)
    (source_dir / "0002_c.webp").write_bytes(sample_webp_bytes)

    output_path = ImagesToPdfConverter().convert(source_dir, tmp_path / "out")

    assert output_path.exists()
    assert output_path.suffix == ".pdf"

    pdf = fitz.open(output_path)
    try:
        assert pdf.page_count == 3
        # Each source image is 512x512; page size should auto-fit it (at
        # the default 72dpi, pixel dimensions map 1:1 to PDF points).
        for page in pdf:
            assert page.rect.width == pytest.approx(512, abs=1)
            assert page.rect.height == pytest.approx(512, abs=1)
            assert len(page.get_images()) == 1
    finally:
        pdf.close()


def test_convert_preserves_upload_order_with_mixed_sizes(
    sample_png_bytes: bytes, tmp_path: Path
) -> None:
    """Order comes from the filename prefix, not the image content — three
    copies of the same real image, differently sized, must appear on pages
    in the exact 0/1/2 order their filenames specify.
    """
    import io

    from PIL import Image

    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Build three distinctly-sized real derivatives from the real PNG bytes.
    src = Image.open(io.BytesIO(sample_png_bytes))
    src.resize((300, 100)).save(source_dir / "0000_first.png")
    src.resize((100, 300)).save(source_dir / "0001_second.png")
    src.resize((200, 200)).save(source_dir / "0002_third.png")

    output_path = ImagesToPdfConverter().convert(source_dir, tmp_path / "out")

    pdf = fitz.open(output_path)
    try:
        assert pdf.page_count == 3
        sizes = [(round(p.rect.width), round(p.rect.height)) for p in pdf]
        assert sizes == [(300, 100), (100, 300), (200, 200)]
    finally:
        pdf.close()


def test_convert_raises_when_no_images_in_directory(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(ValueError, match="No images"):
        ImagesToPdfConverter().convert(empty_dir, tmp_path / "out")
