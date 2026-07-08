"""Execution strategy for running a single conversion — see
app/services/execution_runtime.py's `execute_conversion`, the one place
every tool's actual conversion call goes through regardless of which
strategy its `ConversionSpec` (see conversion_spec.py) declares.
"""

from enum import Enum


class ExecutionMode(Enum):
    #: Runs `converter.convert()` directly, in the calling coroutine — no
    #: thread or process hop. Reserved for genuinely trivial, fast,
    #: low-hang-risk operations. No current tool declares this; it exists
    #: so the runtime and its tests cover all three strategies from day
    #: one, not because anything needs it yet.
    IN_PROCESS = "in_process"

    #: Runs `converter.convert()` in a worker thread (`asyncio.to_thread`),
    #: optionally under a hard `asyncio.wait_for` timeout. The thread
    #: itself cannot be forcibly killed if that timeout fires — see
    #: `execute_conversion`'s docstring for what that does and doesn't
    #: guarantee.
    THREAD = "thread"

    #: Runs the conversion in its own OS subprocess, genuinely killable on
    #: timeout — see `ConversionSpec.process_runner` and
    #: `app/services/conversion.py`'s `_run_worker_subprocess`/
    #: `_terminate_then_kill` (the proven implementation this reuses,
    #: unchanged, rather than a new process-management system).
    PROCESS = "process"
