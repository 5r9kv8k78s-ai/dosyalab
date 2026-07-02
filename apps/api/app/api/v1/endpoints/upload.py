from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.schemas.upload import UploadResponse
from app.services.storage import StorageService

router = APIRouter(tags=["upload"])


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(upload_dir=settings.upload_dir)


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
    storage: StorageService = Depends(get_storage_service),
) -> UploadResponse:
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    file_id, destination, size_bytes = await storage.save(file)

    if size_bytes > max_bytes:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB",
        )

    return UploadResponse(
        file_id=file_id,
        filename=file.filename or "unknown",
        content_type=file.content_type,
        size_bytes=size_bytes,
    )
