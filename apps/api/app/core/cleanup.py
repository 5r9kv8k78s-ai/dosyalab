import asyncio
import logging
import shutil
from datetime import UTC, datetime, timedelta

from app.services.jobs import ConversionJob, job_store

logger = logging.getLogger(__name__)


def _remove_job_files(job: ConversionJob) -> None:
    """Mirrors `run_conversion_job`'s own finally-block cleanup (see
    app/services/conversion.py) — `source_path` is a directory for every
    tool that takes multiple inputs or carries a `params.json` sidecar
    (images-to-pdf, merge-pdf, split-pdf, rotate-pdf, delete-pages,
    extract-pages, reorder-pages, watermark-pdf, protect-pdf, unlock-pdf,
    pdf-to-images, extract-text), a plain file for every other tool.
    `Path.unlink(missing_ok=True)` only suppresses a missing path — called
    on a directory it still raises (IsADirectoryError on Linux,
    PermissionError on macOS), which isn't caught by `missing_ok`.
    `output_path` is always a single file for every tool, never a directory.
    """
    if job.source_path.is_dir():
        shutil.rmtree(job.source_path, ignore_errors=True)
    else:
        job.source_path.unlink(missing_ok=True)
    if job.output_path is not None:
        job.output_path.unlink(missing_ok=True)


def sweep_stale_jobs(ttl_minutes: int) -> int:
    """Delete files and job records for jobs older than `ttl_minutes`.

    Catches clients that submit a job but never poll status or download the
    result, so temporary files don't accumulate on disk indefinitely.
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=ttl_minutes)
    removed = 0

    for job in job_store.all_jobs():
        if job.updated_at > cutoff:
            continue

        try:
            _remove_job_files(job)
            job_store.delete(job.id)
        except Exception:
            # One job's on-disk state (e.g. a permission error, or a race
            # with something else touching the same path) must never stop
            # every other stale job in this sweep — and, since this whole
            # function runs inside `run_periodic_cleanup`'s `asyncio.
            # to_thread` with no other exception handling around it, must
            # never propagate and silently kill the periodic cleanup loop
            # for the rest of the process's lifetime.
            logger.exception("cleanup.job_sweep_failed", extra={"job_id": job.id})
            continue

        removed += 1
        logger.info(
            "cleanup.job_swept",
            extra={"job_id": job.id, "status": job.status, "age_minutes": ttl_minutes},
        )

    return removed


async def run_periodic_cleanup(ttl_minutes: int, interval_minutes: int) -> None:
    """Background loop that sweeps stale jobs every `interval_minutes`."""
    try:
        while True:
            await asyncio.sleep(interval_minutes * 60)
            removed = await asyncio.to_thread(sweep_stale_jobs, ttl_minutes)
            if removed:
                logger.info("cleanup.sweep_complete", extra={"removed": removed})
    except asyncio.CancelledError:
        pass
