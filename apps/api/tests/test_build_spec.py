"""`_build_spec` (see app/services/conversion.py) — resolves each tool's
`ConversionSpec` for `run_conversion_job`'s new dispatch, replacing the
`module_slug`-based if/elif chain that used to decide execution strategy
directly. Confirms every one of the 17 existing tools resolves to exactly
its pre-V2-0 execution behavior, and that an unregistered slug still fails
in a controlled way.
"""

import pytest

from app.core.config import Settings
from app.services.conversion import (
    COMPRESS_PDF_SLUG,
    DELETE_PAGES_SLUG,
    DOCX_TO_PDF_SLUG,
    EXTRACT_IMAGES_SLUG,
    EXTRACT_PAGES_SLUG,
    EXTRACT_TEXT_SLUG,
    IMAGES_TO_PDF_SLUG,
    MERGE_PDF_SLUG,
    PDF_TO_DOCX_SLUG,
    PDF_TO_IMAGES_SLUG,
    PDF_TO_XLSX_SLUG,
    PROTECT_PDF_SLUG,
    REORDER_PAGES_SLUG,
    ROTATE_PDF_SLUG,
    SPLIT_PDF_SLUG,
    UNLOCK_PDF_SLUG,
    WATERMARK_PDF_SLUG,
    _build_spec,
    _convert_pdf_to_docx_isolated,
    run_conversion_job,
)
from app.services.execution_mode import ExecutionMode
from app.services.jobs import job_store

_THREAD_NO_TIMEOUT_SLUGS = [
    PDF_TO_XLSX_SLUG,  # deliberately unchanged this phase — see V2-3
    IMAGES_TO_PDF_SLUG,
    MERGE_PDF_SLUG,
    SPLIT_PDF_SLUG,
    COMPRESS_PDF_SLUG,
    ROTATE_PDF_SLUG,
    DELETE_PAGES_SLUG,
    EXTRACT_PAGES_SLUG,
    REORDER_PAGES_SLUG,
    WATERMARK_PDF_SLUG,
    PROTECT_PDF_SLUG,
    UNLOCK_PDF_SLUG,
    PDF_TO_IMAGES_SLUG,
    EXTRACT_IMAGES_SLUG,
    EXTRACT_TEXT_SLUG,
]


def test_pdf_to_docx_spec_is_process_mode_with_120s_timeout(tmp_path) -> None:
    settings = Settings(convert_output_dir=tmp_path)
    spec = _build_spec(PDF_TO_DOCX_SLUG, settings)
    assert spec.execution_mode == ExecutionMode.PROCESS
    assert spec.timeout_seconds == settings.pdf_to_docx_conversion_timeout_seconds == 120
    # Must be the real, patchable module function — not a copy captured at
    # import time — see _build_spec's own docstring for why.
    assert spec.process_runner is _convert_pdf_to_docx_isolated


def test_docx_to_pdf_spec_is_thread_mode_with_90s_timeout(tmp_path) -> None:
    settings = Settings(convert_output_dir=tmp_path)
    spec = _build_spec(DOCX_TO_PDF_SLUG, settings)
    assert spec.execution_mode == ExecutionMode.THREAD
    assert spec.timeout_seconds == settings.docx_to_pdf_conversion_timeout_seconds == 90
    assert spec.process_runner is None


@pytest.mark.parametrize("slug", _THREAD_NO_TIMEOUT_SLUGS)
def test_every_other_tool_is_thread_mode_with_no_timeout(slug: str, tmp_path) -> None:
    """The exact pre-V2-0 behavior for these 15 tools: a bare
    asyncio.to_thread call, never wrapped in asyncio.wait_for — see
    app/services/execution_runtime.py's execute_conversion for why
    timeout_seconds=None reproduces that precisely."""
    settings = Settings(convert_output_dir=tmp_path)
    spec = _build_spec(slug, settings)
    assert spec.execution_mode == ExecutionMode.THREAD
    assert spec.timeout_seconds is None
    assert spec.process_runner is None


def test_build_spec_reflects_a_monkeypatched_process_runner(monkeypatch, tmp_path) -> None:
    """Proves _build_spec resolves _convert_pdf_to_docx_isolated by a
    fresh name lookup, not a reference captured once — required for every
    existing process-isolation test's monkeypatch.setattr(conversion_module,
    "_convert_pdf_to_docx_isolated", ...) to keep having any effect."""
    import app.services.conversion as conversion_module

    async def _fake(job_id, source_path, destination_dir, timeout_seconds):
        raise AssertionError("should never actually run in this test")

    monkeypatch.setattr(conversion_module, "_convert_pdf_to_docx_isolated", _fake)
    settings = Settings(convert_output_dir=tmp_path)

    spec = conversion_module._build_spec(PDF_TO_DOCX_SLUG, settings)

    assert spec.process_runner is _fake


@pytest.mark.asyncio
async def test_unregistered_slug_fails_the_job_in_a_controlled_way(tmp_path) -> None:
    source_path = tmp_path / "source.bin"
    source_path.write_bytes(b"irrelevant")
    job = job_store.create(
        module_slug="not-a-real-tool", source_path=source_path, download_filename="out.bin"
    )
    settings = Settings(convert_output_dir=tmp_path / "outputs")

    await run_conversion_job(job.id, settings)

    from app.services.jobs import JobStatus

    updated = job_store.get(job.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error is not None
