import logging
from pathlib import Path

from PIL import Image, ImageOps

from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter

logger = logging.getLogger(__name__)

# Balances visual fidelity against file size for the JPEG re-encoding Pillow's
# PDF writer always applies to RGB images (verified empirically — Pillow
# hardcodes DCTDecode/JPEG for mode "RGB" regardless of the source format,
# there's no lossless option for photographic content). 90 is a well-known
# "visually lossless for most content" JPEG quality point; 95+ roughly
# doubles file size for output that's very hard to tell apart from 90.
_JPEG_QUALITY = 90


class ImagesToPdfConverter(ConversionModule):
    """Combines one or more images into a single multi-page PDF, one page
    per image in upload order, each page auto-sized to its image's pixel
    dimensions (verified empirically: Pillow's PDF writer sets each page's
    MediaBox from the image size at the given resolution).

    Unlike the other converters, `source_path` here is a *directory* of
    ordered image files rather than a single file — see
    `submit_images_to_pdf_job` in app/services/conversion.py for how upload
    order is preserved via zero-padded filename prefixes.
    """

    slug = "images-to-pdf"
    input_formats = ("jpg", "jpeg", "png", "webp")
    output_format = "pdf"

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "images.pdf"

        image_paths = sorted(p for p in source_path.iterdir() if p.is_file())
        if not image_paths:
            raise ValueError("No images to convert.")

        logger.info(
            "images_to_pdf.convert.start",
            extra={"source": str(source_path), "image_count": len(image_paths)},
        )

        opened_images = []
        try:
            for path in image_paths:
                image = Image.open(path)
                image.load()
                # Respect the visual orientation phone cameras store as an
                # EXIF tag rather than actually rotating pixels — without
                # this, photos taken in portrait mode can come out sideways.
                image = ImageOps.exif_transpose(image)
                if image.mode not in ("RGB", "L"):
                    # Flattens transparency (RGBA/P) onto white — PDF pages
                    # have no alpha channel concept to preserve here.
                    image = image.convert("RGB")
                opened_images.append(image)

            first_page, remaining_pages = opened_images[0], opened_images[1:]
            first_page.save(
                output_path,
                "PDF",
                save_all=True,
                append_images=remaining_pages,
                quality=_JPEG_QUALITY,
            )
        finally:
            for image in opened_images:
                image.close()

        logger.info(
            "images_to_pdf.convert.done",
            extra={"output": str(output_path), "pages": len(image_paths)},
        )
        return output_path


register_converter(ImagesToPdfConverter())
