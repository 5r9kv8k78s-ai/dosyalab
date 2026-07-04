import uuid
from pathlib import Path
from typing import Callable

from fastapi import UploadFile


class StorageService:
    """Persists uploaded files to disk, keyed by a generated file id.

    Backed by the local filesystem for now; swap the implementation for an
    object-store-backed one (S3, GCS, ...) as the app scales without changing
    callers, since they only depend on this class's interface.
    """

    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        upload: UploadFile,
        on_chunk: Callable[[int], None] | None = None,
    ) -> tuple[str, Path, int]:
        """Streams `upload` to disk in 1MB chunks.

        `on_chunk`, if given, is called with the running byte total after
        every chunk — pass e.g. `lambda total: validate_pdf_size(total, cap)`
        to reject an oversized upload as soon as it crosses the limit,
        instead of only after the entire file has already been written to
        disk. Whatever `on_chunk` raises propagates unchanged (so callers
        keep catching their existing validation error type), and the
        partially-written file is always removed first — on that error or
        any other failure during the write.
        """
        file_id = uuid.uuid4().hex
        suffix = Path(upload.filename or "").suffix
        destination = self.upload_dir / f"{file_id}{suffix}"

        size_bytes = 0
        try:
            with destination.open("wb") as buffer:
                while chunk := await upload.read(1024 * 1024):
                    size_bytes += len(chunk)
                    if on_chunk is not None:
                        on_chunk(size_bytes)
                    buffer.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        return file_id, destination, size_bytes
