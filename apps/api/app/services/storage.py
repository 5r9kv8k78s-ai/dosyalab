import uuid
from pathlib import Path

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

    async def save(self, upload: UploadFile) -> tuple[str, Path, int]:
        file_id = uuid.uuid4().hex
        suffix = Path(upload.filename or "").suffix
        destination = self.upload_dir / f"{file_id}{suffix}"

        size_bytes = 0
        with destination.open("wb") as buffer:
            while chunk := await upload.read(1024 * 1024):
                size_bytes += len(chunk)
                buffer.write(chunk)

        return file_id, destination, size_bytes
