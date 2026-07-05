"""Diagnostic-log regression tests for `run_conversion_job`'s CONVERT_STARTED/
CONVERT_RETURNED/CONVERT_RAISED instrumentation (see app/services/
conversion.py) — added to pin down, from Render's Application Logs, whether a
stuck production job is actually waiting inside `converter.convert()` itself.
These also double as a regression guard that the existing COMPLETED/FAILED
job-status behavior is unchanged by adding the logging.
"""

import logging
from unittest.mock import MagicMock

import fitz
import pytest

import app.services.conversion as conversion_module
from app.core.config import Settings
from app.modules.converter.base import ConversionModule
from app.services.conversion import DOCX_TO_PDF_SLUG, PDF_TO_DOCX_SLUG, run_conversion_job
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


def _make_job(tmp_path, module_slug: str = PDF_TO_DOCX_SLUG):
    source_path = tmp_path / "source.pdf"
    source_path.write_bytes(b"stub source content")
    return job_store.create(
        module_slug=module_slug,
        source_path=source_path,
        download_filename="source.docx",
    )


def _make_real_pdf_job(tmp_path):
    """A job pointing at an actual, PyMuPDF-openable one-page PDF — needed
    to exercise `_pdf_complexity_metrics` on its real, success path (the
    stub bytes `_make_job` writes aren't a valid PDF, which is deliberate
    for the fail-open tests below)."""
    source_path = tmp_path / "real.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "complexity metrics test")
    doc.save(source_path)
    doc.close()
    return job_store.create(
        module_slug=PDF_TO_DOCX_SLUG,
        source_path=source_path,
        download_filename="real.docx",
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


@pytest.mark.asyncio
async def test_convert_started_includes_complexity_metrics_for_pdf_to_docx(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _InstantConverter())
    job = _make_real_pdf_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    started = next(r for r in caplog.records if r.msg == "convert.convert_started")
    assert started.page_count == 1
    assert started.file_size_bytes > 0
    assert started.total_images == 0
    assert started.total_drawings == 0
    assert started.text_char_count > 0

    assert not any(r.msg == "convert.complexity_metrics_failed" for r in caplog.records)


@pytest.mark.asyncio
async def test_complexity_metrics_failure_is_fail_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    # _make_job's source.pdf is deliberately not a real PDF, so PyMuPDF
    # fails to open it inside _pdf_complexity_metrics.
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _InstantConverter())
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    warning = next(r for r in caplog.records if r.msg == "convert.complexity_metrics_failed")
    assert warning.job_id == job.id
    assert warning.tool_slug == PDF_TO_DOCX_SLUG
    assert isinstance(warning.exception_type, str) and warning.exception_type

    started = next(r for r in caplog.records if r.msg == "convert.convert_started")
    assert not hasattr(started, "page_count")
    assert not hasattr(started, "total_images")

    # Behavior guard: a metrics failure must never affect the conversion —
    # the job still completes exactly as it would without this instrumentation.
    assert any(r.msg == "convert.convert_returned" for r in caplog.records)
    updated_job = job_store.get(job.id)
    assert updated_job is not None
    assert updated_job.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_complexity_preflight_only_runs_for_pdf_to_docx(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    metrics_mock = MagicMock(side_effect=AssertionError("should not be called for this tool"))
    monkeypatch.setattr(conversion_module, "_pdf_complexity_metrics", metrics_mock)

    class _OtherToolConverter(ConversionModule):
        slug = DOCX_TO_PDF_SLUG
        input_formats = ("docx",)
        output_format = "pdf"

        def convert(self, source_path, destination_dir):
            destination_dir.mkdir(parents=True, exist_ok=True)
            output_path = destination_dir / f"{source_path.stem}.pdf"
            output_path.write_bytes(b"stub pdf output")
            return output_path

    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _OtherToolConverter())
    job = _make_job(tmp_path, module_slug=DOCX_TO_PDF_SLUG)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    metrics_mock.assert_not_called()
    started = next(r for r in caplog.records if r.msg == "convert.convert_started")
    assert not hasattr(started, "page_count")
    updated_job = job_store.get(job.id)
    assert updated_job is not None
    assert updated_job.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_logs_never_contain_source_path_or_filename(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _InstantConverter())
    job = _make_real_pdf_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    forbidden = (str(job.source_path), job.source_path.name, job.download_filename)
    for record in caplog.records:
        rendered = record.getMessage() + " " + " ".join(str(v) for v in vars(record).values())
        for value in forbidden:
            assert value not in rendered
