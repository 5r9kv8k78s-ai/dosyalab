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

Deliberately logs nothing itself: the parent process owns all structured
logging for this job (see conversion.py's convert.process_* events), and
this worker's own stdout/stderr must never carry a filename, path, or file
content — only a bare output-path line on success (stdout) or a non-zero
exit code on failure (stderr is discarded by the parent).
"""

import sys
from pathlib import Path

from app.modules.converter.pdf_to_docx import PdfToDocxConverter


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        return 2

    source_path = Path(argv[1])
    destination_dir = Path(argv[2])

    try:
        output_path = PdfToDocxConverter().convert(source_path, destination_dir)
    except Exception:
        return 1

    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
