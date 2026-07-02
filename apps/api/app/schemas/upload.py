from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    content_type: str | None
    size_bytes: int
