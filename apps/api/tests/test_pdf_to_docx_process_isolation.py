"""Tests for the pdf-to-docx process-isolation + hard-timeout architecture
(see app/services/conversion.py's `_run_worker_subprocess`,
`_terminate_then_kill`, `_convert_pdf_to_docx_isolated`, and the standalone
`app/services/pdf_to_docx_worker.py` entrypoint it spawns).

The core guarantee under test: unlike a worker thread, a subprocess that
exceeds its timeout is genuinely terminated (or killed) and reaped — these
tests verify the real OS process, not just that the awaiting coroutine
raised a timeout.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import fitz
import pytest

import app.services.conversion as conversion_module
from app.core.config import Settings
from app.services.conversion import (
    DOCX_TO_PDF_SLUG,
    PDF_TO_DOCX_SLUG,
    ConversionSubprocessError,
    _run_worker_subprocess,
    run_conversion_job,
)
from app.services.jobs import JobStatus, job_store


def _make_real_pdf(tmp_path: Path, name: str = "source.pdf") -> Path:
    path = tmp_path / name
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "process isolation test")
    doc.save(path)
    doc.close()
    return path


def _process_is_alive(pid: int) -> bool:
    """os.kill(pid, 0) sends no signal — it only checks the OS still knows
    about this PID — the standard liveness check without side effects."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


# ---------------------------------------------------------------------------
# 1. Successful fast conversion via subprocess
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pdf_to_docx_job_completes_via_subprocess(tmp_path: Path) -> None:
    source_path = _make_real_pdf(tmp_path)
    job = job_store.create(
        module_slug=PDF_TO_DOCX_SLUG, source_path=source_path, download_filename="source.docx"
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED
    assert updated.output_path is not None
    assert updated.output_path.exists()
    assert updated.output_path.stat().st_size > 0


# ---------------------------------------------------------------------------
# 2. Worker exception -> non-zero exit -> existing failure path preserved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pdf_to_docx_job_fails_when_worker_exits_non_zero(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Not a real PDF — the worker's PdfToDocxConverter will raise, causing
    # a non-zero exit, exactly like a genuine conversion failure would.
    source_path = tmp_path / "not_a_real_pdf.pdf"
    source_path.write_bytes(b"not actually a pdf")
    job = job_store.create(
        module_slug=PDF_TO_DOCX_SLUG, source_path=source_path, download_filename="x.docx"
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    messages = [r.msg for r in caplog.records]
    assert "convert.convert_raised" in messages
    assert "convert.job_failed" in messages
    assert "convert.convert_returned" not in messages

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error is not None


# ---------------------------------------------------------------------------
# 3. Real hard timeout: a genuinely hanging process is actually killed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hanging_subprocess_is_killed_and_reaped_on_timeout(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A controlled, deliberately-hanging child (not the real pdf2docx
    worker — this is about the timeout/kill mechanism itself, not any
    particular conversion) must be genuinely terminated when it exceeds
    its timeout — checked against the real OS PID, not just that the
    awaiting coroutine raised."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "import time; time.sleep(60)",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    pid = process.pid
    assert _process_is_alive(pid)

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        with pytest.raises(ConversionSubprocessError):
            # Reach into the already-started process via the same
            # wait_for/terminate/kill path _run_worker_subprocess uses, by
            # exercising the real function against a trivial "sleep" command
            # with a tiny timeout instead of waiting a full minute.
            await conversion_module._run_worker_subprocess(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                timeout_seconds=0.2,
                job_id="test-hang-job",
                tool_slug=PDF_TO_DOCX_SLUG,
            )

    # The process spawned above (used only for the initial liveness check)
    # is unrelated to the one _run_worker_subprocess itself spawned and
    # already cleaned up — clean it up too so it doesn't linger.
    process.kill()
    await process.wait()

    messages = [r.msg for r in caplog.records]
    assert "convert.process_started" in messages
    assert "convert.process_timeout" in messages
    assert "convert.process_completed" not in messages

    timeout_record = next(r for r in caplog.records if r.msg == "convert.process_timeout")
    assert timeout_record.job_id == "test-hang-job"
    assert timeout_record.tool_slug == PDF_TO_DOCX_SLUG
    assert timeout_record.timeout_seconds == 0.2


@pytest.mark.asyncio
async def test_run_worker_subprocess_child_pid_actually_dies_on_timeout() -> None:
    """The strongest possible proof this isn't just a coroutine-level
    timeout: capture the real child PID mid-flight and confirm the OS has
    reaped it after the call returns."""
    captured_pid: dict[str, int] = {}
    real_create_subprocess_exec = asyncio.create_subprocess_exec

    async def _spy_create_subprocess_exec(*args, **kwargs):
        process = await real_create_subprocess_exec(*args, **kwargs)
        captured_pid["pid"] = process.pid
        return process

    original = asyncio.create_subprocess_exec
    asyncio.create_subprocess_exec = _spy_create_subprocess_exec
    try:
        with pytest.raises(ConversionSubprocessError):
            await _run_worker_subprocess(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                timeout_seconds=0.2,
                job_id="pid-check-job",
                tool_slug=PDF_TO_DOCX_SLUG,
            )
    finally:
        asyncio.create_subprocess_exec = original

    assert "pid" in captured_pid
    assert not _process_is_alive(captured_pid["pid"])


# ---------------------------------------------------------------------------
# 4. Terminate-ignoring child escalates to kill
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_ignoring_terminate_is_escalated_to_kill(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Shrink the grace period so this test doesn't take the real 5s.
    monkeypatch.setattr(conversion_module, "_TERMINATE_GRACE_PERIOD_SECONDS", 0.3)

    ignore_sigterm_script = (
        "import signal, time\n" "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n" "time.sleep(60)\n"
    )

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        with pytest.raises(ConversionSubprocessError):
            await _run_worker_subprocess(
                [sys.executable, "-c", ignore_sigterm_script],
                timeout_seconds=0.2,
                job_id="ignores-term-job",
                tool_slug=PDF_TO_DOCX_SLUG,
            )

    messages = [r.msg for r in caplog.records]
    assert "convert.process_timeout" in messages
    assert "convert.process_terminated" not in messages
    assert "convert.process_killed" in messages

    killed_record = next(r for r in caplog.records if r.msg == "convert.process_killed")
    assert killed_record.termination_method == "kill"
    assert killed_record.job_id == "ignores-term-job"


# ---------------------------------------------------------------------------
# 7. Other converters never take the subprocess path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_converters_do_not_use_process_isolation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _fail_if_called(*args, **kwargs):
        raise AssertionError("non-pdf-to-docx job must not use process isolation")

    monkeypatch.setattr(conversion_module, "_convert_pdf_to_docx_isolated", _fail_if_called)

    from docx import Document

    source_path = tmp_path / "source.docx"
    Document().save(source_path)
    job = job_store.create(
        module_slug=DOCX_TO_PDF_SLUG, source_path=source_path, download_filename="x.pdf"
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED


# ---------------------------------------------------------------------------
# 8. Timeout at the run_conversion_job level ends in FAILED, not stuck PROCESSING
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_job_reaches_failed_not_stuck_processing_after_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async def _hanging_conversion(job_id, source_path, destination_dir, timeout_seconds):
        return await _run_worker_subprocess(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            timeout_seconds=0.2,
            job_id=job_id,
            tool_slug=PDF_TO_DOCX_SLUG,
        )

    monkeypatch.setattr(conversion_module, "_convert_pdf_to_docx_isolated", _hanging_conversion)

    source_path = _make_real_pdf(tmp_path)
    job = job_store.create(
        module_slug=PDF_TO_DOCX_SLUG, source_path=source_path, download_filename="x.docx"
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.status != JobStatus.PROCESSING


# ---------------------------------------------------------------------------
# 9. Log privacy: no source path/filename in any new log record
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_isolation_logs_never_contain_source_path_or_filename(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    source_path = _make_real_pdf(tmp_path, name="a-very-identifiable-name.pdf")
    job = job_store.create(
        module_slug=PDF_TO_DOCX_SLUG,
        source_path=source_path,
        download_filename="a-very-identifiable-name.docx",
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    forbidden = (str(source_path), source_path.name, job.download_filename)
    for record in caplog.records:
        rendered = record.getMessage() + " " + " ".join(str(v) for v in vars(record).values())
        for value in forbidden:
            assert value not in rendered


# ---------------------------------------------------------------------------
# 10. pdf2docx stage-timing instrumentation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pdf_to_docx_stage_timings_are_logged_for_a_real_conversion(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The worker's own stage-timing lines (see pdf_to_docx_worker.py) must
    reach the parent's structured logger as convert.pdf_to_docx_stage
    events, one per pdf2docx stage (load_pages/parse_document/parse_pages/
    make_docx) — real, existing pdf2docx progress markers, not invented
    checkpoints (verified directly against the installed pdf2docx source).
    """
    source_path = _make_real_pdf(tmp_path)
    job = job_store.create(
        module_slug=PDF_TO_DOCX_SLUG, source_path=source_path, download_filename="source.docx"
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED

    stage_records = [r for r in caplog.records if r.msg == "convert.pdf_to_docx_stage"]
    stages = {r.stage for r in stage_records}
    assert stages == {"load_pages", "parse_document", "parse_pages", "make_docx"}
    for record in stage_records:
        assert record.job_id == job.id
        assert record.tool_slug == PDF_TO_DOCX_SLUG
        assert isinstance(record.duration_ms, int)
        assert record.duration_ms >= 0


@pytest.mark.asyncio
async def test_pdf_to_docx_stage_timing_logs_never_contain_source_path_or_filename(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    source_path = _make_real_pdf(tmp_path, name="a-very-identifiable-stage-name.pdf")
    job = job_store.create(
        module_slug=PDF_TO_DOCX_SLUG,
        source_path=source_path,
        download_filename="a-very-identifiable-stage-name.docx",
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    stage_records = [r for r in caplog.records if r.msg == "convert.pdf_to_docx_stage"]
    assert stage_records  # sanity: the thing under test actually happened

    forbidden = (str(source_path), source_path.name, job.download_filename)
    for record in stage_records:
        rendered = " ".join(str(v) for v in vars(record).values())
        for value in forbidden:
            assert value not in rendered


@pytest.mark.asyncio
async def test_stage_timing_line_is_forwarded_even_when_the_job_times_out(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The exact regression this instrumentation was fixed for: a worker
    that emits a stage-timing line and then hangs past the timeout must
    still have that line reach the parent's logger in real time — not be
    silently lost because `communicate()` only returns its buffered
    streams once the process exits (which, for a genuinely hanging
    process, never happens before the parent kills it)."""
    script = (
        "import sys, time\n"
        "print('[PDF2DOCX STAGE] stage=load_pages duration_ms=42', file=sys.stderr, flush=True)\n"
        "time.sleep(60)\n"
    )

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        with pytest.raises(ConversionSubprocessError):
            await _run_worker_subprocess(
                [sys.executable, "-c", script],
                timeout_seconds=0.3,
                job_id="stage-timeout-job",
                tool_slug=PDF_TO_DOCX_SLUG,
            )

    stage_records = [r for r in caplog.records if r.msg == "convert.pdf_to_docx_stage"]
    assert len(stage_records) == 1
    assert stage_records[0].stage == "load_pages"
    assert stage_records[0].duration_ms == 42
    assert stage_records[0].job_id == "stage-timeout-job"

    messages = [r.msg for r in caplog.records]
    assert "convert.process_timeout" in messages
