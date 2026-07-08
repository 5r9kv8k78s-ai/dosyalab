import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class JobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ConversionJob:
    id: str
    module_slug: str
    source_path: Path
    download_filename: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    output_path: Path | None = None
    error: str | None = None
    # Internal failure classification (see app/services/failure_taxonomy.py)
    # — never returned by the API (see app/schemas/convert.py's
    # ConvertJobStatus, which has no field for it). `error` above remains
    # the only user-facing message, unchanged.
    error_code: str | None = None
    # How many input files this job started from (1 for every single-file
    # tool; the real count for merge-pdf/images-to-pdf) — kept only for the
    # operations-events summary (see services/operations_events.py), never
    # exposed with filenames or content.
    file_count: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class JobStore:
    """In-memory registry of conversion jobs.

    Single-process only — fine for this deployment, but if DosyaLab ever
    runs multiple API replicas, this needs to move to a shared store (e.g.
    Redis) so status polling and downloads hit the replica that owns the job.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, ConversionJob] = {}
        self._lock = threading.Lock()

    def create(
        self,
        module_slug: str,
        source_path: Path,
        download_filename: str,
        file_count: int = 1,
    ) -> ConversionJob:
        job = ConversionJob(
            id=uuid.uuid4().hex,
            module_slug=module_slug,
            source_path=source_path,
            download_filename=download_filename,
            file_count=file_count,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> ConversionJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields: object) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            job.updated_at = datetime.now(UTC)

    def delete(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def all_jobs(self) -> list[ConversionJob]:
        with self._lock:
            return list(self._jobs.values())


job_store = JobStore()
