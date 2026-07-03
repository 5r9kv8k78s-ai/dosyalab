from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, populated from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DosyaLab API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Comma-separated list of exact allowed CORS origins.
    cors_origins: str = "http://localhost:3000"

    # Optional regex for origins that can't be pinned to one exact value —
    # e.g. Vercel mints a new preview URL per branch/PR, so listing them all
    # in CORS_ORIGINS isn't practical. Scope this to your own project, e.g.
    # CORS_ORIGIN_REGEX=https://dosyalab.*\.vercel\.app — left unset (no
    # regex matching) by default rather than defaulting to something broad
    # like every *.vercel.app subdomain, since that would accept credentialed
    # requests from other people's Vercel projects too.
    cors_origin_regex: str | None = None

    @field_validator("cors_origin_regex", mode="before")
    @classmethod
    def _blank_regex_means_unset(cls, value: str | None) -> str | None:
        # pydantic-settings reads `CORS_ORIGIN_REGEX=` (blank) as `""`, not
        # `None` — and `""` is a valid regex that matches every string, which
        # would silently turn into "allow any origin" for a credentialed CORS
        # policy. Treat blank the same as unset.
        if value is not None and not value.strip():
            return None
        return value

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
