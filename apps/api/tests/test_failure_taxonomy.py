"""`_classify_failure` (see app/services/conversion.py) and the
`FailureCode` contract it maps to (see app/services/failure_taxonomy.py) —
V2-2's internal, never-user-facing failure classification for
`ConversionJob.error_code`. Exercised at the `run_conversion_job` level so
these are regression tests against the real dispatch, not just the pure
mapping function in isolation.
"""

import logging
import sys

import pytest

import app.services.conversion as conversion_module
from app.core.config import Settings
from app.modules.converter.base import ConversionModule, VerificationResult
from app.services.conversion import (
    DOCX_TO_PDF_SLUG,
    PDF_TO_DOCX_SLUG,
    ConversionSubprocessError,
    _run_worker_subprocess,
    run_conversion_job,
)
from app.services.failure_taxonomy import FailureCode
from app.services.jobs import JobStatus, job_store


def _make_job(tmp_path, module_slug: str = DOCX_TO_PDF_SLUG, filename: str = "source.docx"):
    source_path = tmp_path / filename
    source_path.write_bytes(b"stub source content")
    return job_store.create(
        module_slug=module_slug, source_path=source_path, download_filename="source.pdf"
    )


def _make_real_pdf_job(tmp_path):
    import fitz

    source_path = tmp_path / "real.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "failure taxonomy test")
    doc.save(source_path)
    doc.close()
    return job_store.create(
        module_slug=PDF_TO_DOCX_SLUG, source_path=source_path, download_filename="real.docx"
    )


class _SlowConverter(ConversionModule):
    """Sleeps past a short THREAD timeout — mirrors test_docx_to_pdf_timeout.py."""

    slug = DOCX_TO_PDF_SLUG
    input_formats = ("docx",)
    output_format = "pdf"

    def convert(self, source_path, destination_dir):
        import time

        time.sleep(5)
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.pdf"
        output_path.write_bytes(b"stub pdf output")
        return output_path


class _RaisingConverter(ConversionModule):
    slug = DOCX_TO_PDF_SLUG
    input_formats = ("docx",)
    output_format = "pdf"

    def convert(self, source_path, destination_dir):
        raise RuntimeError("simulated engine failure")


def _make_verify_converter(reason: str | None, *, ok: bool = False) -> type[ConversionModule]:
    class _VerifyConverter(ConversionModule):
        slug = DOCX_TO_PDF_SLUG
        input_formats = ("docx",)
        output_format = "pdf"

        def convert(self, source_path, destination_dir):
            destination_dir.mkdir(parents=True, exist_ok=True)
            output_path = destination_dir / f"{source_path.stem}.pdf"
            output_path.write_bytes(b"stub pdf output")
            return output_path

        def verify(self, output_path):
            return VerificationResult(ok=ok, reason=reason)

    return _VerifyConverter


class _RaisingVerifyConverter(ConversionModule):
    slug = DOCX_TO_PDF_SLUG
    input_formats = ("docx",)
    output_format = "pdf"

    def convert(self, source_path, destination_dir):
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.pdf"
        output_path.write_bytes(b"stub pdf output")
        return output_path

    def verify(self, output_path):
        raise RuntimeError("simulated verifier bug")


@pytest.mark.asyncio
async def test_thread_mode_timeout_is_classified_as_conversion_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _SlowConverter())
    job = _make_job(tmp_path)
    settings = Settings(
        convert_output_dir=tmp_path / "outputs", docx_to_pdf_conversion_timeout_seconds=1
    )

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error_code == FailureCode.CONVERSION_TIMEOUT
    assert "unsupported features" in updated.error


@pytest.mark.asyncio
async def test_process_mode_timeout_is_classified_as_conversion_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    async def _hanging_conversion(job_id, source_path, destination_dir, timeout_seconds):
        return await _run_worker_subprocess(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            timeout_seconds=0.2,
            job_id=job_id,
            tool_slug=PDF_TO_DOCX_SLUG,
        )

    monkeypatch.setattr(conversion_module, "_convert_pdf_to_docx_isolated", _hanging_conversion)
    job = _make_real_pdf_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error_code == FailureCode.CONVERSION_TIMEOUT
    assert "unsupported features" in updated.error


@pytest.mark.asyncio
async def test_process_mode_non_zero_exit_is_engine_failure_not_timeout(tmp_path) -> None:
    """A subprocess that exits non-zero (a real engine crash) must NOT be
    classified as a timeout, even though both raise ConversionSubprocessError
    — this is exactly what ConversionSubprocessError.timed_out distinguishes."""
    with pytest.raises(ConversionSubprocessError) as excinfo:
        await _run_worker_subprocess(
            [sys.executable, "-c", "import sys; sys.exit(1)"],
            timeout_seconds=5,
            job_id="non-zero-exit-job",
            tool_slug=PDF_TO_DOCX_SLUG,
        )
    assert excinfo.value.timed_out is False
    assert conversion_module._classify_failure(excinfo.value) == FailureCode.ENGINE_FAILURE


@pytest.mark.asyncio
async def test_converter_exception_is_classified_as_engine_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _RaisingConverter())
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error_code == FailureCode.ENGINE_FAILURE
    assert "unsupported features" in updated.error


@pytest.mark.asyncio
async def test_verification_output_missing_is_classified_correctly(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        conversion_module, "get_converter", lambda slug: _make_verify_converter("output_missing")()
    )
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error_code == FailureCode.OUTPUT_MISSING


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["invalid_pdf", "invalid_xlsx"])
async def test_verification_invalid_output_is_classified_correctly(
    monkeypatch: pytest.MonkeyPatch, tmp_path, reason: str
) -> None:
    monkeypatch.setattr(
        conversion_module, "get_converter", lambda slug: _make_verify_converter(reason)()
    )
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error_code == FailureCode.OUTPUT_INVALID


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["zero_pages", "no_worksheets"])
async def test_verification_no_meaningful_output_is_classified_correctly(
    monkeypatch: pytest.MonkeyPatch, tmp_path, reason: str
) -> None:
    monkeypatch.setattr(
        conversion_module, "get_converter", lambda slug: _make_verify_converter(reason)()
    )
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error_code == FailureCode.NO_MEANINGFUL_OUTPUT


@pytest.mark.asyncio
async def test_verifier_exception_is_classified_as_output_invalid(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    """Fail-closed: a verifier that itself crashed couldn't confirm the
    output was valid, so it's treated as OUTPUT_INVALID rather than
    ENGINE_FAILURE (the engine/convert() call already succeeded by then)
    or a silent pass-through."""
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _RaisingVerifyConverter())
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error_code == FailureCode.OUTPUT_INVALID

    messages = [r.msg for r in caplog.records]
    assert "convert.verification_raised" in messages
    # Distinct from a deliberate ok=False rejection: no verification_result
    # log, since verify() never returned.
    assert "convert.verification_result" not in messages


@pytest.mark.asyncio
async def test_successful_conversion_has_no_error_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        conversion_module, "get_converter", lambda slug: _make_verify_converter(None, ok=True)()
    )
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED
    assert updated.error_code is None
    assert updated.error is None


@pytest.mark.asyncio
async def test_failure_logs_never_contain_source_path_or_filename(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _RaisingConverter())
    job = _make_job(tmp_path, filename="a-very-identifiable-name.docx")
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    forbidden = (str(job.source_path), job.source_path.name, job.download_filename)
    for record in caplog.records:
        rendered = record.getMessage() + " " + " ".join(str(v) for v in vars(record).values())
        for value in forbidden:
            assert value not in rendered
