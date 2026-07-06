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

    # A 100MB-per-file limit still permits an abusive batch total on
    # multi-file endpoints (merge-pdf, images-to-pdf) — e.g. 200 files at
    # just under the per-file cap. This bounds the file *count* per request;
    # it does not replace `max_convert_upload_size_mb`, which still applies
    # to each individual file in the batch.
    max_batch_file_count: int = 30

    # How long a completed/failed job's files are kept before the periodic
    # sweep deletes them, for clients that never call the download endpoint.
    job_ttl_minutes: int = 60
    cleanup_interval_minutes: int = 10

    # Hard ceiling for a single pdf-to-docx conversion, run in its own
    # killable OS process (see app/services/conversion.py's
    # `_run_worker_subprocess`) rather than a plain worker thread — some
    # real-world PDFs make pdf2docx's layout/table reconstruction take an
    # unbounded amount of time, and only a real process can be forcibly
    # terminated if that happens. Not enforced for other converters.
    pdf_to_docx_conversion_timeout_seconds: int = 120

    # Ceiling for a single docx-to-pdf conversion (see app/services/
    # conversion.py's `_convert_with_timeout`) — xhtml2pdf is a pure-Python
    # HTML/CSS renderer with no C-level GIL release, so a pathological or
    # very large DOCX can make it run far longer than a normal document
    # would. Enforced with asyncio.wait_for around the existing worker
    # thread, not a separate OS process: the underlying thread can't be
    # forcibly killed and keeps running in the background after this fires,
    # but the job is released as FAILED immediately rather than staying in
    # PROCESSING forever — see that risk assessment for why process
    # isolation wasn't judged necessary here the way it was for pdf-to-docx.
    docx_to_pdf_conversion_timeout_seconds: int = 90

    # Public-production abuse protection for the conversion/upload surface
    # (see app/services/rate_limiter.py) — a process-local fixed-window
    # limiter, since no shared datastore (Redis, etc.) exists in this
    # deployment yet. 20 requests per 60s per client is generous for normal
    # interactive use (a batch upload is one request, not one per file)
    # while still blocking rapid automated abuse.
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 20
    rate_limit_window_seconds: int = 60

    # Privacy-safe operational event tracking for the future Admin Panel
    # (see app/services/operations_events.py) — in-memory only, bounded by
    # both a max event count and a retention window so it can never grow
    # unbounded. 5000 events / 7 days is a lightweight V1 default; a real
    # datastore is required before this is relied on for production
    # reporting (events are lost on restart and are per-replica).
    operations_events_enabled: bool = True
    operations_events_max_count: int = 5000
    operations_events_retention_seconds: int = 7 * 24 * 60 * 60

    # Which OperationsEventStore implementation to use — "memory" (default,
    # safe for local dev/tests) or "postgres" (real persistence, requires
    # DATABASE_URL). Explicit rather than inferred from whether
    # DATABASE_URL happens to be set, so a misconfigured production
    # deployment fails loudly instead of silently running on memory.
    operations_store_backend: str = "memory"

    # Backend-only Postgres connection string (Supabase-hosted or any other
    # Postgres). NEVER exposed to the web app — see apps/web/.env.example,
    # which has no equivalent variable.
    database_url: str | None = None

    # Supabase project URL, used server-side to fetch the project's JWKS
    # for verifying Admin Panel access tokens (see app/services/admin_auth.py).
    # The browser has its own copy via NEXT_PUBLIC_SUPABASE_URL — same
    # value, different variable, since NEXT_PUBLIC_* and backend-only
    # settings are read from separate .env files in this monorepo.
    supabase_url: str | None = None
    # Optional — only set if your Supabase project's access tokens carry a
    # non-default `aud` claim you want strictly checked.
    supabase_jwt_audience: str | None = None

    # Backend-only allowlist of admin emails — the actual authorization
    # boundary for every /api/v1/admin/* route. A valid Supabase session
    # alone does not make a user an admin; their verified email must also
    # appear here. Never exposed to the browser (no NEXT_PUBLIC_ equivalent).
    admin_emails: str = ""

    @property
    def admin_email_set(self) -> frozenset[str]:
        return frozenset(
            email.strip().lower() for email in self.admin_emails.split(",") if email.strip()
        )

    # Separate rate-limit policy for the public feedback endpoint — kept
    # independent of the conversion limiter's budget (see
    # app/services/rate_limiter.py) so a burst of feedback submissions
    # can't exhaust a client's conversion quota, or vice versa. Deliberately
    # conservative: feedback is an occasional action, not a workflow.
    feedback_rate_limit_enabled: bool = True
    feedback_rate_limit_requests: int = 5
    feedback_rate_limit_window_seconds: int = 600

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
