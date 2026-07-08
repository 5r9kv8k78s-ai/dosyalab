"""Standalone entrypoint for running a single pdf-to-docx conversion in its
own OS process — invoked via `sys.executable -m app.services.pdf_to_docx_worker
<source_path> <destination_dir>` (see `app/services/conversion.py`'s
`_run_worker_subprocess`), never with `shell=True`.

Isolated in its own process (rather than a worker thread, the pattern every
other converter still uses) specifically so a pathological, unbounded
pdf2docx call can be forcibly terminated/killed by the parent on timeout — a
thread cannot be. This module runs the real `PdfToDocxConverter`, so the
non-RGB image compatibility fix (see pdf_to_docx.py) is active here exactly
as it is in-process.

This worker's own stdout/stderr must never carry a filename, path, or file
content: stdout carries only the bare output-path line on success; stderr
carries only fixed-prefix stage-timing lines (see `_StageTimingHandler`
below) that `conversion.py`'s `_run_worker_subprocess` forwards to its own
structured logger — anything else on stderr is discarded by the parent,
never logged.

Stage boundaries are pdf2docx's own, existing internal progress markers
(`Converter.load_pages`/`parse_document`/`parse_pages`/`make_docx`, each
logging a fixed "[N/4] ..." line via the bare `logging` module — verified
directly against the installed pdf2docx==0.5.8 source) — not invented
checkpoints, and `convert()` itself is still called exactly as before, so
conversion behavior is unchanged.

Each stage's line is printed and flushed the moment the *next* stage
begins (not batched up and printed only after the whole conversion
finishes) — a process killed by the parent on timeout, mid-conversion,
never reaches any "after convert() returns/raises" code at all, so
deferring every line to that point would mean a job that times out
produces no stage output whatsoever, no matter how promptly the parent
reads its stderr.
"""

import logging
import sys
import time
from pathlib import Path

from app.modules.converter.pdf_to_docx import PdfToDocxConverter

_STAGE_PREFIX = "[PDF2DOCX STAGE]"

# pdf2docx's Converter.parse()/convert() logs exactly these 4 fixed,
# content-free progress markers, in this order, via the bare `logging`
# module (see pdf2docx.converter.Converter.load_pages/parse_document/
# parse_pages/make_docx) — never a filename or document content.
_STAGE_MARKERS = (
    ("[1/4]", "load_pages"),
    ("[2/4]", "parse_document"),
    ("[3/4]", "parse_pages"),
    ("[4/4]", "make_docx"),
)


def _emit_stage_line(stage: str, duration_ms: int) -> None:
    # flush=True regardless of whether stderr would default to line- or
    # block-buffered when redirected to a pipe (as it always is here) —
    # this must reach the OS pipe the instant it's printed, not whenever
    # Python's own io buffering next decides to write it out.
    print(f"{_STAGE_PREFIX} stage={stage} duration_ms={duration_ms}", file=sys.stderr, flush=True)


class _StageTimingHandler(logging.Handler):
    """Prints one safe, fixed-prefix stage-timing line to stderr *as soon
    as the next stage begins* — ignores every other log record pdf2docx
    emits (per-page progress, "Start to convert <path>", error text),
    never storing or forwarding their content.
    """

    def __init__(self, start_time: float) -> None:
        super().__init__(level=logging.INFO)
        self._start_time = start_time
        self._stage_start_ms: dict[str, int] = {}
        self._last_stage: str | None = None

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        for marker, stage in _STAGE_MARKERS:
            if marker not in message or stage in self._stage_start_ms:
                continue
            now_ms = int((time.perf_counter() - self._start_time) * 1000)
            self._stage_start_ms[stage] = now_ms
            if self._last_stage is not None:
                _emit_stage_line(self._last_stage, now_ms - self._stage_start_ms[self._last_stage])
            self._last_stage = stage
            return

    def flush_final_stage(self) -> None:
        """Emits the duration of the last stage reached — the one
        `emit()` never got to close out, because either it's genuinely
        the last stage (make_docx) or the conversion raised partway
        through it. A stage that never started at all gets no line ever,
        never a fabricated duration. Safe to call more than once."""
        if self._last_stage is None:
            return
        total_ms = int((time.perf_counter() - self._start_time) * 1000)
        _emit_stage_line(self._last_stage, total_ms - self._stage_start_ms[self._last_stage])
        self._last_stage = None


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        return 2

    source_path = Path(argv[1])
    destination_dir = Path(argv[2])

    start_time = time.perf_counter()
    handler = _StageTimingHandler(start_time)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    try:
        output_path = PdfToDocxConverter().convert(source_path, destination_dir)
    except Exception:
        handler.flush_final_stage()
        return 1
    finally:
        root_logger.removeHandler(handler)

    handler.flush_final_stage()
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
