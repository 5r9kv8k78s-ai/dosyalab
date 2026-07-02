import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.services.jobs import job_store

logger = logging.getLogger(__name__)


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

        job.source_path.unlink(missing_ok=True)
        if job.output_path is not None:
            job.output_path.unlink(missing_ok=True)

        job_store.delete(job.id)
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
