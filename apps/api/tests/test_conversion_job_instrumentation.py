"""Diagnostic-log regression tests for `run_conversion_job`'s CONVERT_STARTED/
CONVERT_RETURNED/CONVERT_RAISED instrumentation (see app/services/
conversion.py) — added to pin down, from Render's Application Logs, whether a
stuck production job is actually waiting inside `converter.convert()` itself.
These also double as a regression guard that the existing COMPLETED/FAILED
job-status behavior is unchanged by adding the logging.
"""

import logging

import pytest

import app.services.conversion as conversion_module
from app.core.config import Settings
from app.modules.converter.base import ConversionModule
from app.services.conversion import PDF_TO_DOCX_SLUG, run_conversion_job
from app.services.jobs import JobStatus, job_store


class _InstantConverter(ConversionModule):
    slug = PDF_TO_DOCX_SLUG
    input_formats = ("pdf",)
    output_format = "docx"

    def convert(self, source_path, destination_dir):
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.docx"
        output_path.write_bytes(b"stub docx output")
        return output_path


class _RaisingConverter(ConversionModule):
    slug = PDF_TO_DOCX_SLUG
    input_formats = ("pdf",)
    output_format = "docx"

    def convert(self, source_path, destination_dir):
        raise RuntimeError("simulated converter failure")


def _make_job(tmp_path):
    source_path = tmp_path / "source.pdf"
    source_path.write_bytes(b"stub source content")
    return job_store.create(
        module_slug=PDF_TO_DOCX_SLUG,
        source_path=source_path,
        download_filename="source.docx",
    )


@pytest.mark.asyncio
async def test_convert_started_and_returned_logged_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _InstantConverter())
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    messages = [record.msg for record in caplog.records]
    assert "convert.convert_started" in messages
    assert "convert.convert_returned" in messages
    assert "convert.convert_raised" not in messages

    started = next(r for r in caplog.records if r.msg == "convert.convert_started")
    assert started.job_id == job.id
    assert started.tool_slug == PDF_TO_DOCX_SLUG
    assert not hasattr(started, "elapsed_ms")  # spec: elapsed_ms only on the outcome logs

    returned = next(r for r in caplog.records if r.msg == "convert.convert_returned")
    assert returned.job_id == job.id
    assert returned.tool_slug == PDF_TO_DOCX_SLUG
    assert returned.elapsed_ms >= 0

    # Behavior guard: job status/completion semantics are unchanged.
    updated_job = job_store.get(job.id)
    assert updated_job is not None
    assert updated_job.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_convert_raised_logged_and_job_still_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _RaisingConverter())
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    messages = [record.msg for record in caplog.records]
    assert "convert.convert_started" in messages
    assert "convert.convert_raised" in messages
    assert "convert.convert_returned" not in messages
    # The existing job-failure log still fires — the new instrumentation
    # doesn't replace it, just adds a converter-boundary-specific signal.
    assert "convert.job_failed" in messages

    raised = next(r for r in caplog.records if r.msg == "convert.convert_raised")
    assert raised.job_id == job.id
    assert raised.tool_slug == PDF_TO_DOCX_SLUG
    assert raised.elapsed_ms >= 0

    # Behavior guard: the exception still reaches the existing FAILED path
    # unchanged — this instrumentation only observes it, never swallows it.
    updated_job = job_store.get(job.id)
    assert updated_job is not None
    assert updated_job.status == JobStatus.FAILED
    assert updated_job.error is not None
