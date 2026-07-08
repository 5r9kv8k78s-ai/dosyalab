"""`execute_conversion` (see app/services/execution_runtime.py) — the V2-0
Foundation's single execution-strategy dispatch point. Exercised directly,
independent of any real converter/subprocess, so these tests stay fast and
isolated from app/services/conversion.py entirely (execution_runtime.py
has no import from that module, by design — see its own docstring).
"""

import asyncio
import time
from pathlib import Path

import pytest

from app.modules.converter.base import ConversionModule
from app.services.conversion_spec import ConversionSpec
from app.services.execution_mode import ExecutionMode
from app.services.execution_runtime import execute_conversion


class _RecordingConverter(ConversionModule):
    """Records which thread it ran on and how long convert() took to be
    invoked — enough to prove IN_PROCESS never hops to a worker thread."""

    slug = "test-tool"
    input_formats = ("pdf",)
    output_format = "pdf"

    def __init__(self, *, delay_seconds: float = 0.0) -> None:
        self.delay_seconds = delay_seconds
        self.called_from_thread_name: str | None = None

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        import threading

        self.called_from_thread_name = threading.current_thread().name
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}_output.pdf"
        output_path.write_bytes(b"stub output")
        return output_path


@pytest.mark.asyncio
async def test_in_process_mode_calls_converter_directly_on_the_event_loop_thread(
    tmp_path: Path,
) -> None:
    import threading

    converter = _RecordingConverter()
    spec = ConversionSpec(slug="test-tool", execution_mode=ExecutionMode.IN_PROCESS)

    result = await execute_conversion(
        spec, converter, tmp_path / "in.pdf", tmp_path, job_id="job-1"
    )

    assert result.exists()
    assert converter.called_from_thread_name == threading.current_thread().name


@pytest.mark.asyncio
async def test_thread_mode_runs_converter_on_a_worker_thread(tmp_path: Path) -> None:
    import threading

    converter = _RecordingConverter()
    spec = ConversionSpec(slug="test-tool", execution_mode=ExecutionMode.THREAD)

    result = await execute_conversion(
        spec, converter, tmp_path / "in.pdf", tmp_path, job_id="job-2"
    )

    assert result.exists()
    assert converter.called_from_thread_name != threading.current_thread().name


@pytest.mark.asyncio
async def test_thread_mode_with_no_timeout_never_raises_timeout_error(tmp_path: Path) -> None:
    """Every THREAD-mode tool except docx-to-pdf has timeout_seconds=None
    (see app/services/conversion.py's _build_spec) — this must behave
    exactly like a bare asyncio.to_thread call, never enforcing any limit."""
    converter = _RecordingConverter(delay_seconds=0.1)
    spec = ConversionSpec(
        slug="test-tool", execution_mode=ExecutionMode.THREAD, timeout_seconds=None
    )

    result = await execute_conversion(
        spec, converter, tmp_path / "in.pdf", tmp_path, job_id="job-3"
    )
    assert result.exists()


@pytest.mark.asyncio
async def test_thread_mode_timeout_raises_timeout_error(tmp_path: Path) -> None:
    converter = _RecordingConverter(delay_seconds=5)
    spec = ConversionSpec(
        slug="test-tool", execution_mode=ExecutionMode.THREAD, timeout_seconds=0.2
    )

    with pytest.raises(TimeoutError):
        await execute_conversion(spec, converter, tmp_path / "in.pdf", tmp_path, job_id="job-4")


@pytest.mark.asyncio
async def test_process_mode_delegates_entirely_to_the_spec_process_runner(tmp_path: Path) -> None:
    """PROCESS mode must not add its own timeout wrapper on top of the
    process_runner — the runner (see app/services/conversion.py's
    _convert_pdf_to_docx_isolated/_run_worker_subprocess) already owns its
    own timeout/terminate/kill lifecycle end to end."""
    calls: list[tuple] = []

    async def _fake_process_runner(job_id, source_path, destination_dir, timeout_seconds):
        calls.append((job_id, source_path, destination_dir, timeout_seconds))
        return destination_dir / "process_output.pdf"

    converter = _RecordingConverter()  # never called for PROCESS mode
    spec = ConversionSpec(
        slug="pdf-to-docx",
        execution_mode=ExecutionMode.PROCESS,
        timeout_seconds=120,
        process_runner=_fake_process_runner,
    )

    result = await execute_conversion(
        spec, converter, tmp_path / "in.pdf", tmp_path, job_id="job-5"
    )

    assert result == tmp_path / "process_output.pdf"
    assert calls == [("job-5", tmp_path / "in.pdf", tmp_path, 120)]
    assert converter.called_from_thread_name is None  # converter.convert() itself was never called


@pytest.mark.asyncio
async def test_process_mode_propagates_process_runner_timeout_error(tmp_path: Path) -> None:
    class _FakeSubprocessError(Exception):
        pass

    async def _timing_out_runner(job_id, source_path, destination_dir, timeout_seconds):
        raise _FakeSubprocessError("simulated timeout+kill, already handled by the runner")

    converter = _RecordingConverter()
    spec = ConversionSpec(
        slug="pdf-to-docx",
        execution_mode=ExecutionMode.PROCESS,
        timeout_seconds=120,
        process_runner=_timing_out_runner,
    )

    with pytest.raises(_FakeSubprocessError):
        await execute_conversion(spec, converter, tmp_path / "in.pdf", tmp_path, job_id="job-6")


@pytest.mark.asyncio
async def test_unhandled_execution_mode_raises_a_controlled_error(tmp_path: Path) -> None:
    """Defensive guard, not reachable via any of today's 17 real tool
    specs (ExecutionMode has exactly 3 members) — but a spec somehow
    carrying an unrecognized mode must fail loudly and specifically,
    never silently misbehave."""
    converter = _RecordingConverter()
    spec = ConversionSpec.__new__(ConversionSpec)
    object.__setattr__(spec, "slug", "mystery-tool")
    object.__setattr__(spec, "execution_mode", "not-a-real-mode")
    object.__setattr__(spec, "timeout_seconds", None)
    object.__setattr__(spec, "process_runner", None)

    with pytest.raises(ValueError, match="Unhandled execution mode"):
        await execute_conversion(spec, converter, tmp_path / "in.pdf", tmp_path, job_id="job-7")


@pytest.mark.asyncio
async def test_concurrent_thread_mode_conversions_do_not_interfere(tmp_path: Path) -> None:
    """Sanity check that execute_conversion's THREAD path is safe to run
    concurrently for independent jobs — matches how run_conversion_job is
    actually invoked (one call per background task, potentially
    overlapping in time)."""
    converters = [_RecordingConverter(delay_seconds=0.05) for _ in range(5)]
    specs = [
        ConversionSpec(slug="test-tool", execution_mode=ExecutionMode.THREAD) for _ in converters
    ]

    results = await asyncio.gather(
        *[
            execute_conversion(spec, conv, tmp_path / f"in{i}.pdf", tmp_path, job_id=f"job-{i}")
            for i, (spec, conv) in enumerate(zip(specs, converters, strict=True))
        ]
    )

    assert all(r.exists() for r in results)
