"""Regression test for a production hang: `run_conversion_job` used to call
`record_operations_event` directly (synchronous, un-threaded) after marking
the job COMPLETED. When `OPERATIONS_STORE_BACKEND=postgres` and that write is
slow/unresponsive, this single-worker process's entire event loop would
freeze for its duration — including the frontend's own job-status polling —
even though the job itself had already finished. See app/services/
conversion.py's `run_conversion_job` for the `asyncio.to_thread` fix this
guards.
"""

import asyncio
import time

import fitz
import pytest

import app.services.conversion as conversion_module
from app.core.config import Settings
from app.services.conversion import PDF_TO_DOCX_SLUG, run_conversion_job
from app.services.jobs import JobStatus, job_store


@pytest.mark.asyncio
async def test_run_conversion_job_does_not_block_event_loop_during_event_recording(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # Stands in for a slow/hanging Postgres write without touching a real
    # database — a plain blocking call, exactly the shape record_operations_
    # event has when OPERATIONS_STORE_BACKEND=postgres.
    def slow_record(*args: object, **kwargs: object) -> None:
        time.sleep(1.0)

    monkeypatch.setattr(conversion_module, "record_operations_event", slow_record)

    # A minimal one-page PDF generated on the fly — this test cares about
    # event-loop concurrency around the *recording* call, not conversion
    # correctness (already covered elsewhere), so it doesn't need the full
    # real-world fixture.
    source_path = tmp_path / "tiny.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "concurrency test")
    doc.save(source_path)
    doc.close()

    job = job_store.create(
        module_slug=PDF_TO_DOCX_SLUG,
        source_path=source_path,
        download_filename="tiny.docx",
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    tick_times: list[float] = []
    job_done = asyncio.Event()

    async def run_and_signal() -> None:
        await run_conversion_job(job.id, settings)
        job_done.set()

    async def tick_until_job_done() -> None:
        # Stands in for other concurrent work this event loop must keep
        # serving — e.g. a frontend polling GET /jobs/{id} for this same
        # job — for as long as the job itself is running, so it necessarily
        # overlaps the (now-threaded) event-recording call at the end,
        # whatever the real conversion's own duration turns out to be.
        while not job_done.is_set():
            await asyncio.sleep(0.05)
            tick_times.append(time.monotonic())

    await asyncio.gather(run_and_signal(), tick_until_job_done())

    updated_job = job_store.get(job.id)
    assert updated_job is not None
    assert updated_job.status == JobStatus.COMPLETED

    # If the event-recording write ever blocks the loop again, every tick
    # due during that ~1s window is delayed until it returns, landing back
    # to back in one burst afterward instead of at their ~0.05s spacing —
    # a gap this much larger than the scheduled interval (but well under
    # the 1s block) only shows up in that broken scenario.
    gaps = [b - a for a, b in zip(tick_times, tick_times[1:])]
    assert max(gaps) < 0.3, f"tick gaps were not evenly spaced: {gaps}"
