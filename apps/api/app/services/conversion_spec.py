"""`ConversionSpec` — the per-tool execution metadata `run_conversion_job`
(see app/services/conversion.py) dispatches on, replacing the
`module_slug`-based if/elif chain that used to decide execution strategy
there directly. See app/services/execution_runtime.py's
`execute_conversion`, the single place every spec is actually acted on.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from app.services.execution_mode import ExecutionMode

#: Signature every PROCESS-mode spec's `process_runner` must match — see
#: app/services/conversion.py's `_convert_pdf_to_docx_isolated` for the one
#: implementation this phase actually uses.
ProcessRunner = Callable[[str, Path, Path, float], Awaitable[Path]]


@dataclass(frozen=True)
class ConversionSpec:
    slug: str
    execution_mode: ExecutionMode

    #: `None` means no timeout is enforced at all — the exact behavior
    #: every THREAD-mode tool except docx-to-pdf already had before this
    #: phase (a bare `asyncio.to_thread` call, never wrapped in
    #: `asyncio.wait_for`). Passing `None` to `asyncio.wait_for` is
    #: documented to behave identically to awaiting the future directly,
    #: so `execute_conversion` doesn't need a separate no-timeout code path.
    timeout_seconds: float | None = None

    #: Required when `execution_mode` is `PROCESS` (enforced below) —
    #: deliberately a caller-supplied callable rather than a generic
    #: subprocess spawner built fresh in the runtime: this phase has
    #: exactly one PROCESS-mode tool (pdf-to-docx), and reuses its already
    #: proven `_convert_pdf_to_docx_isolated` as-is, unmodified, so every
    #: existing process-isolation test (which monkeypatches that exact
    #: function, and `_run_worker_subprocess`/`_terminate_then_kill`
    #: underneath it, by name) keeps passing unchanged.
    process_runner: ProcessRunner | None = None

    def __post_init__(self) -> None:
        if self.execution_mode == ExecutionMode.PROCESS and self.process_runner is None:
            raise ValueError(
                f"ConversionSpec for '{self.slug}' declares PROCESS execution "
                "but has no process_runner."
            )
