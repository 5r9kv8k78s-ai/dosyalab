from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, populated from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FormatFlow API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Comma-separated list of allowed CORS origins.
    cors_origins: str = "http://localhost:3000"

    # Where uploaded files are stored before being handed to a conversion module.
    upload_dir: Path = Path("storage/uploads")
    max_upload_size_mb: int = 25

    # Conversion pipeline (async job) storage and limits.
    convert_upload_dir: Path = Path("storage/convert/uploads")
    convert_output_dir: Path = Path("storage/convert/outputs")
    max_convert_upload_size_mb: int = 100

    # How long a completed/failed job's files are kept before the periodic
    # sweep deletes them, for clients that never call the download endpoint.
    job_ttl_minutes: int = 60
    cleanup_interval_minutes: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
