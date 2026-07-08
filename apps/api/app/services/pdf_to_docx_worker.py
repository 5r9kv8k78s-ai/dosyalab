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


class _StageTimingHandler(logging.Handler):
    """Notes, per pdf2docx stage marker, how many ms had elapsed (since
    `start_time`) when that stage began — ignores every other log record
    pdf2docx emits (per-page progress, "Start to convert <path>", error
    text), never storing or forwarding their content.
    """

    def __init__(self, start_time: float) -> None:
        super().__init__(level=logging.INFO)
        self._start_time = start_time
        self.stage_start_ms: dict[str, int] = {}

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        for marker, stage in _STAGE_MARKERS:
            if marker in message and stage not in self.stage_start_ms:
                self.stage_start_ms[stage] = int((time.perf_counter() - self._start_time) * 1000)
                return


def _print_stage_timings(stage_start_ms: dict[str, int], start_time: float) -> None:
    """Prints one safe, fixed-prefix line per stage that actually started,
    to stderr — a stage that never started (e.g. a crash before reaching
    it) gets no line at all, never a fabricated duration."""
    total_ms = int((time.perf_counter() - start_time) * 1000)
    stage_names = [stage for _, stage in _STAGE_MARKERS]
    for i, stage in enumerate(stage_names):
        if stage not in stage_start_ms:
            continue
        next_stage = stage_names[i + 1] if i + 1 < len(stage_names) else None
        end_ms = stage_start_ms.get(next_stage, total_ms) if next_stage else total_ms
        duration_ms = end_ms - stage_start_ms[stage]
        print(f"{_STAGE_PREFIX} stage={stage} duration_ms={duration_ms}", file=sys.stderr)


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
        _print_stage_timings(handler.stage_start_ms, start_time)
        return 1
    finally:
        root_logger.removeHandler(handler)

    _print_stage_timings(handler.stage_start_ms, start_time)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
