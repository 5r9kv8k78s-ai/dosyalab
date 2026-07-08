"""`ConversionSpec` (see app/services/conversion_spec.py) — the V2-0
Foundation's per-tool execution metadata.
"""

import pytest

from app.services.conversion_spec import ConversionSpec
from app.services.execution_mode import ExecutionMode


def test_thread_spec_with_no_timeout_is_valid() -> None:
    spec = ConversionSpec(slug="merge-pdf", execution_mode=ExecutionMode.THREAD)
    assert spec.timeout_seconds is None
    assert spec.process_runner is None


def test_thread_spec_with_timeout_is_valid() -> None:
    spec = ConversionSpec(
        slug="docx-to-pdf", execution_mode=ExecutionMode.THREAD, timeout_seconds=90
    )
    assert spec.timeout_seconds == 90


def test_in_process_spec_is_valid() -> None:
    spec = ConversionSpec(slug="noop", execution_mode=ExecutionMode.IN_PROCESS)
    assert spec.process_runner is None


def test_process_spec_requires_a_process_runner() -> None:
    async def _runner(job_id, source_path, destination_dir, timeout_seconds):
        raise NotImplementedError

    with pytest.raises(ValueError, match="process_runner"):
        ConversionSpec(slug="pdf-to-docx", execution_mode=ExecutionMode.PROCESS)

    # Providing one makes the same spec valid.
    spec = ConversionSpec(
        slug="pdf-to-docx",
        execution_mode=ExecutionMode.PROCESS,
        timeout_seconds=120,
        process_runner=_runner,
    )
    assert spec.process_runner is _runner


def test_spec_is_frozen() -> None:
    spec = ConversionSpec(slug="merge-pdf", execution_mode=ExecutionMode.THREAD)
    with pytest.raises(AttributeError):
        spec.slug = "something-else"  # type: ignore[misc]
