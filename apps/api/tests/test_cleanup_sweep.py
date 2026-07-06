"""`sweep_stale_jobs` (see app/core/cleanup.py) — the periodic sweep that
deletes files/records for jobs a client never polled or downloaded.

Regression coverage for a real bug found during a conversion-engine
architecture review: `source_path` is a *directory* for every tool that
takes multiple inputs or carries a `params.json` sidecar (images-to-pdf,
merge-pdf, split-pdf, rotate-pdf, delete-pages, extract-pages,
reorder-pages, watermark-pdf, protect-pdf, unlock-pdf, pdf-to-images,
extract-text) — the sweep used to call `Path.unlink(missing_ok=True)`
unconditionally, which raises on a directory (`missing_ok` only suppresses
a *missing* path, not a wrong-type one). Since `sweep_stale_jobs` runs
inside `run_periodic_cleanup`'s `asyncio.to_thread` with no other exception
handling around it, that single unhandled error silently killed the
periodic cleanup loop for the rest of the process's lifetime.
"""

from datetime import UTC, datetime, timedelta

from app.core.cleanup import sweep_stale_jobs
from app.services.jobs import JobStatus, job_store


def _make_stale(job_id: str, minutes_old: int = 120) -> None:
    # JobStore.update() always stamps updated_at to "now" as its last step
    # (see app/services/jobs.py), so it can't be used to backdate a job —
    # mutate the stored dataclass instance directly instead.
    job = job_store.get(job_id)
    assert job is not None
    job.updated_at = datetime.now(UTC) - timedelta(minutes=minutes_old)


def test_sweep_removes_stale_single_file_job(tmp_path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"stub")
    output = tmp_path / "output.docx"
    output.write_bytes(b"stub")

    job = job_store.create(
        module_slug="pdf-to-docx", source_path=source, download_filename="out.docx"
    )
    job_store.update(job.id, status=JobStatus.COMPLETED, output_path=output)
    _make_stale(job.id)

    removed = sweep_stale_jobs(ttl_minutes=60)

    assert removed == 1
    assert job_store.get(job.id) is None
    assert not source.exists()
    assert not output.exists()


def test_sweep_removes_stale_directory_based_job_without_raising(tmp_path) -> None:
    """The regression case: a directory source_path (merge-pdf, split-pdf,
    images-to-pdf, and every other params.json-sidecar tool) must not crash
    the sweep."""
    source_dir = tmp_path / "job-input"
    source_dir.mkdir()
    (source_dir / "0000.pdf").write_bytes(b"stub")
    (source_dir / "params.json").write_text("{}")

    job = job_store.create(
        module_slug="merge-pdf", source_path=source_dir, download_filename="merged.pdf"
    )
    _make_stale(job.id)

    removed = sweep_stale_jobs(ttl_minutes=60)

    assert removed == 1
    assert job_store.get(job.id) is None
    assert not source_dir.exists()


def test_sweep_does_not_touch_fresh_jobs(tmp_path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"stub")
    job = job_store.create(
        module_slug="pdf-to-docx", source_path=source, download_filename="out.docx"
    )
    # Left at its just-created updated_at — well within the TTL window.

    removed = sweep_stale_jobs(ttl_minutes=60)

    assert removed == 0
    assert job_store.get(job.id) is not None
    assert source.exists()


def test_sweep_continues_after_one_job_fails(tmp_path, monkeypatch) -> None:
    """One job's on-disk cleanup failing must not stop the rest of the
    sweep, and must not raise out of sweep_stale_jobs (which would kill
    run_periodic_cleanup's loop permanently — see module docstring)."""
    import app.core.cleanup as cleanup_module

    good_source = tmp_path / "good.pdf"
    good_source.write_bytes(b"stub")
    good_job = job_store.create(
        module_slug="pdf-to-docx", source_path=good_source, download_filename="good.docx"
    )
    _make_stale(good_job.id)

    bad_source = tmp_path / "bad.pdf"
    bad_source.write_bytes(b"stub")
    bad_job = job_store.create(
        module_slug="pdf-to-docx", source_path=bad_source, download_filename="bad.docx"
    )
    _make_stale(bad_job.id)

    original_remove = cleanup_module._remove_job_files

    def _fail_for_bad_job(job):
        if job.id == bad_job.id:
            raise OSError("simulated failure")
        return original_remove(job)

    monkeypatch.setattr(cleanup_module, "_remove_job_files", _fail_for_bad_job)

    removed = sweep_stale_jobs(ttl_minutes=60)

    assert removed == 1
    assert job_store.get(good_job.id) is None
    assert not good_source.exists()
    # The failed job is left in place rather than silently deleted from the
    # store while its files remain on disk — it's picked up again on the
    # next sweep.
    assert job_store.get(bad_job.id) is not None
    assert bad_source.exists()
