from pydantic import BaseModel


class ConvertJobCreated(BaseModel):
    job_id: str
    status: str


class ConvertJobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    filename: str
    error: str | None = None
    download_url: str | None = None
