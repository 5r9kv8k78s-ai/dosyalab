"""docx-to-pdf's hard timeout (see app/services/conversion.py's
`_convert_with_timeout`) — xhtml2pdf is a pure-Python HTML/CSS renderer
with no bound on how long it can run, unlike every other converter that
still runs via plain `asyncio.to_thread`. This does not use process
isolation the way pdf-to-docx does (see the Faz B risk assessment for why
that was judged unnecessary here): the underlying thread can't be killed
and keeps running in the background, but the job itself is released as
FAILED promptly instead of staying in PROCESSING forever.
"""

import time

import pytest

import app.services.conversion as conversion_module
from app.core.config import Settings
from app.modules.converter.base import ConversionModule
from app.services.conversion import DOCX_TO_PDF_SLUG, run_conversion_job
from app.services.jobs import JobStatus, job_store


class _SlowConverter(ConversionModule):
    slug = DOCX_TO_PDF_SLUG
    input_formats = ("docx",)
    output_format = "pdf"

    def convert(self, source_path, destination_dir):
        time.sleep(5)
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.pdf"
        output_path.write_bytes(b"stub pdf output")
        return output_path


class _InstantDocxToPdfConverter(ConversionModule):
    slug = DOCX_TO_PDF_SLUG
    input_formats = ("docx",)
    output_format = "pdf"

    def convert(self, source_path, destination_dir):
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.pdf"
        output_path.write_bytes(b"stub pdf output")
        return output_path


def _make_job(tmp_path):
    source_path = tmp_path / "source.docx"
    source_path.write_bytes(b"stub docx content")
    return job_store.create(
        module_slug=DOCX_TO_PDF_SLUG, source_path=source_path, download_filename="source.pdf"
    )


@pytest.mark.asyncio
async def test_docx_to_pdf_times_out_and_job_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _SlowConverter())
    job = _make_job(tmp_path)
    settings = Settings(
        convert_output_dir=tmp_path / "outputs", docx_to_pdf_conversion_timeout_seconds=1
    )

    with caplog.at_level("WARNING", logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error is not None

    messages = [record.msg for record in caplog.records]
    assert "convert.thread_timeout" in messages
    timeout_record = next(r for r in caplog.records if r.msg == "convert.thread_timeout")
    assert timeout_record.job_id == job.id
    assert timeout_record.tool_slug == DOCX_TO_PDF_SLUG


@pytest.mark.asyncio
async def test_docx_to_pdf_completes_normally_within_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        conversion_module, "get_converter", lambda slug: _InstantDocxToPdfConverter()
    )
    job = _make_job(tmp_path)
    settings = Settings(
        convert_output_dir=tmp_path / "outputs", docx_to_pdf_conversion_timeout_seconds=30
    )

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED
    assert updated.output_path is not None
    assert updated.output_path.exists()


@pytest.mark.asyncio
async def test_docx_to_pdf_timeout_setting_does_not_affect_other_converters(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Scope guard: a tiny docx_to_pdf_conversion_timeout_seconds must not
    somehow throttle an unrelated tool still running the plain
    asyncio.to_thread path."""
    from app.services.conversion import COMPRESS_PDF_SLUG

    class _SlowCompressConverter(ConversionModule):
        slug = COMPRESS_PDF_SLUG
        input_formats = ("pdf",)
        output_format = "pdf"

        def convert(self, source_path, destination_dir):
            time.sleep(0.1)
            destination_dir.mkdir(parents=True, exist_ok=True)
            output_path = destination_dir / f"{source_path.stem}.pdf"
            output_path.write_bytes(b"stub compressed pdf")
            return output_path

    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _SlowCompressConverter())
    source_path = tmp_path / "source.pdf"
    source_path.write_bytes(b"stub pdf content")
    job = job_store.create(
        module_slug=COMPRESS_PDF_SLUG, source_path=source_path, download_filename="source.pdf"
    )
    # Even docx-to-pdf's own timeout at its practical minimum must have zero
    # effect on a completely different tool, since compress-pdf never reads
    # this setting at all — it still runs via the plain asyncio.to_thread
    # path in run_conversion_job.
    settings = Settings(
        convert_output_dir=tmp_path / "outputs", docx_to_pdf_conversion_timeout_seconds=1
    )

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED
