"""The single place every conversion's actual execution strategy is
carried out — see app/services/conversion_spec.py's `ConversionSpec` for
how a tool declares which strategy it needs, and app/services/
conversion.py's `run_conversion_job` for the orchestration layer that
calls this (job state, success/failure handling, cleanup) without itself
knowing anything about threads, processes, or timeouts.

Deliberately has no import from app/services/conversion.py: PROCESS mode's
concrete subprocess mechanics are injected via `ConversionSpec.
process_runner` rather than re-implemented or imported here, so this
module carries zero risk of a circular import with the module that builds
specs, and stays testable in isolation with a fake process_runner.
"""

import asyncio
from pathlib import Path

from app.modules.converter.base import ConversionModule
from app.services.conversion_spec import ConversionSpec
from app.services.execution_mode import ExecutionMode


async def execute_conversion(
    spec: ConversionSpec,
    converter: ConversionModule,
    source_path: Path,
    destination_dir: Path,
    *,
    job_id: str,
) -> Path:
    """Runs `converter.convert(source_path, destination_dir)` under
    whichever strategy `spec.execution_mode` declares, returning the
    resulting output path.

    Raises whatever the underlying strategy raises — a bare exception from
    `converter.convert` (IN_PROCESS), `TimeoutError` from a THREAD-mode
    timeout, or `ConversionSubprocessError` (see conversion.py) from a
    PROCESS-mode failure/timeout. This function never catches or
    normalizes any of these; `run_conversion_job` is the one place that
    turns any of them into the job's FAILED state.
    """
    if spec.execution_mode == ExecutionMode.PROCESS:
        # spec.process_runner is guaranteed non-None here — ConversionSpec.
        # __post_init__ already enforced that for any PROCESS-mode spec.
        return await spec.process_runner(job_id, source_path, destination_dir, spec.timeout_seconds)  # type: ignore[misc]

    if spec.execution_mode == ExecutionMode.THREAD:
        return await asyncio.wait_for(
            asyncio.to_thread(converter.convert, source_path, destination_dir),
            timeout=spec.timeout_seconds,
        )

    if spec.execution_mode == ExecutionMode.IN_PROCESS:
        return converter.convert(source_path, destination_dir)

    raise ValueError(f"Unhandled execution mode for '{spec.slug}': {spec.execution_mode!r}")
