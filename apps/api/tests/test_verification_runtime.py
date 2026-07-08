"""V2-1's runtime wiring: `run_conversion_job` now calls `converter.verify()`
after `execute_conversion` succeeds and before the job is marked COMPLETED
(see app/services/conversion.py). Exercises this at the `run_conversion_job`
level with converter test doubles, independent of any real converter's
verify() implementation (see test_docx_to_pdf_verify.py / test_pdf_to_xlsx_
verify.py for those) — and independent of app/services/execution_runtime.py,
which has no notion of verification at all.
"""

import logging
import shutil
from pathlib import Path

import pytest

import app.services.conversion as conversion_module
from app.core.config import Settings
from app.modules.converter.base import ConversionModule, VerificationResult
from app.services.conversion import DOCX_TO_PDF_SLUG, PDF_TO_XLSX_SLUG, run_conversion_job
from app.services.jobs import JobStatus, job_store


def _make_job(tmp_path, module_slug: str = DOCX_TO_PDF_SLUG):
    source_path = tmp_path / "source.docx"
    source_path.write_bytes(b"stub source content")
    return job_store.create(
        module_slug=module_slug, source_path=source_path, download_filename="source.pdf"
    )


class _DefaultVerifyConverter(ConversionModule):
    """Never overrides verify() — inherits the base no-op (ok=True)."""

    slug = DOCX_TO_PDF_SLUG
    input_formats = ("docx",)
    output_format = "pdf"

    def convert(self, source_path, destination_dir):
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.pdf"
        output_path.write_bytes(b"stub pdf output")
        return output_path


class _RejectingConverter(ConversionModule):
    slug = DOCX_TO_PDF_SLUG
    input_formats = ("docx",)
    output_format = "pdf"

    def convert(self, source_path, destination_dir):
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.pdf"
        output_path.write_bytes(b"stub pdf output")
        return output_path

    def verify(self, output_path):
        return VerificationResult(ok=False, reason="simulated_rejection")


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
async def test_default_verify_still_completes_the_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    """Regression guard: a converter that doesn't override verify() (14 of
    the 17 tools, post-V2-1) must behave exactly as it did before V2-1."""
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _DefaultVerifyConverter())
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED

    verification = next(r for r in caplog.records if r.msg == "convert.verification_result")
    assert verification.verification_ok is True
    assert verification.verification_reason is None
    assert verification.verification_duration_ms >= 0


@pytest.mark.asyncio
async def test_verification_result_ok_false_fails_the_job_generically(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _RejectingConverter())
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    # Same generic, pre-existing user-facing error contract — no new
    # error_code/failure-taxonomy field introduced this phase.
    assert updated.error is not None
    assert "unsupported features" in updated.error

    messages = [r.msg for r in caplog.records]
    assert "convert.verification_result" in messages
    assert "convert.job_failed" in messages

    verification = next(r for r in caplog.records if r.msg == "convert.verification_result")
    assert verification.verification_ok is False
    assert verification.verification_reason == "simulated_rejection"


@pytest.mark.asyncio
async def test_verification_exception_fails_the_job_the_same_generic_way(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    """A bug inside verify() itself (as opposed to a deliberate ok=False)
    must reach the exact same FAILED path — run_conversion_job's existing
    outer `except Exception:` already covers this without any special-casing,
    since the verify() call sits inside that same try block."""
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _RaisingVerifyConverter())
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error is not None

    messages = [r.msg for r in caplog.records]
    assert "convert.job_failed" in messages
    # Distinct from the ok=False case: no convert.verification_result log
    # was ever emitted, because verify() raised before it could return.
    assert "convert.verification_result" not in messages


@pytest.mark.asyncio
async def test_verification_logs_never_contain_source_path_or_filename(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(conversion_module, "get_converter", lambda slug: _RejectingConverter())
    job = _make_job(tmp_path)
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    forbidden = (str(job.source_path), job.source_path.name, job.download_filename)
    for record in caplog.records:
        rendered = record.getMessage() + " " + " ".join(str(v) for v in vars(record).values())
        for value in forbidden:
            assert value not in rendered


@pytest.mark.asyncio
async def test_real_docx_to_pdf_pipeline_passes_verification_and_completes(
    sample_docx_path: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """End-to-end through the real, registered DocxToPdfConverter (not a
    test double) — proves the real verify() override is actually wired into
    run_conversion_job's success path, not just unit-testable in isolation."""
    source_path = tmp_path / "source.docx"
    shutil.copy(sample_docx_path, source_path)  # run_conversion_job unlinks source_path
    job = job_store.create(
        module_slug=DOCX_TO_PDF_SLUG, source_path=source_path, download_filename="source.pdf"
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED

    verification = next(r for r in caplog.records if r.msg == "convert.verification_result")
    assert verification.verification_ok is True
    assert verification.verification_reason is None


@pytest.mark.asyncio
async def test_real_pdf_to_xlsx_pipeline_passes_verification_and_completes(
    sample_pdf_path: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """End-to-end through the real, registered PdfToXlsxConverter — the real
    fixture has extractable tables (see test_pdf_to_xlsx_converter.py), so
    this exercises the actual success path, not a stub."""
    source_path = tmp_path / "source.pdf"
    shutil.copy(sample_pdf_path, source_path)
    job = job_store.create(
        module_slug=PDF_TO_XLSX_SLUG, source_path=source_path, download_filename="source.xlsx"
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    with caplog.at_level(logging.INFO, logger="app.services.conversion"):
        await run_conversion_job(job.id, settings)

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED

    verification = next(r for r in caplog.records if r.msg == "convert.verification_result")
    assert verification.verification_ok is True
    assert verification.verification_reason is None
