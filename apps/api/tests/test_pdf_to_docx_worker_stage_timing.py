"""`_StageTimingHandler` (see app/services/pdf_to_docx_worker.py) — this is
the actual producer of the stage-timing lines app/services/conversion.py's
`_run_worker_subprocess` forwards in real time (see that module's own
tests). A prior version of this handler only *recorded* stage boundaries
and deferred all printing to a single batch after `PdfToDocxConverter.
convert()` returned or raised — meaning a job the parent kills mid-
conversion (e.g. on timeout) never reached that code at all, so nothing
was ever written to stderr for the parent to forward, no matter how
promptly it read that stream (confirmed against real production logs: a
120.1s timeout with zero convert.pdf_to_docx_stage events). These tests
exercise the handler directly, independent of any real pdf2docx run, so
they can assert on line-by-line stderr output *before* the conversion as a
whole ever finishes.
"""

import logging

from app.services.pdf_to_docx_worker import _STAGE_MARKERS, _StageTimingHandler


def _fire(handler: _StageTimingHandler, marker: str) -> None:
    record = logging.LogRecord(
        name="root", level=logging.INFO, pathname="", lineno=0, msg=marker, args=(), exc_info=None
    )
    handler.emit(record)


def test_a_stage_line_prints_as_soon_as_the_next_stage_begins(capsys) -> None:
    """The exact real-time guarantee under test: stage 1's line must be
    on stderr the moment stage 2 begins — not only after
    flush_final_stage() (which stands in for "the whole conversion is
    over"), since a killed-mid-conversion process never reaches that."""
    handler = _StageTimingHandler(start_time=0.0)

    _fire(handler, "[1/4] Opening document...")
    assert capsys.readouterr().err == ""  # nothing to report yet — no prior stage to close out

    _fire(handler, "[2/4] Analyzing document...")
    captured = capsys.readouterr()
    assert "[PDF2DOCX STAGE] stage=load_pages duration_ms=" in captured.err
    assert "parse_document" not in captured.err  # not started yet, so not reported yet


def test_all_four_stages_stream_progressively_not_batched_at_the_end(capsys) -> None:
    lines_after_each_marker = []
    handler = _StageTimingHandler(start_time=0.0)
    for marker, _ in _STAGE_MARKERS:
        _fire(handler, marker)
        lines_after_each_marker.append(capsys.readouterr().err)

    # Each of the first 3 markers closes out the *previous* stage — the
    # 4th (make_docx starting) closes out parse_pages. make_docx itself
    # is only ever closed out by flush_final_stage(), simulating the
    # worker actually finishing (or raising) — see the next test.
    assert lines_after_each_marker[0] == ""
    assert "stage=load_pages" in lines_after_each_marker[1]
    assert "stage=parse_document" in lines_after_each_marker[2]
    assert "stage=parse_pages" in lines_after_each_marker[3]

    handler.flush_final_stage()
    assert "stage=make_docx" in capsys.readouterr().err


def test_a_stage_that_never_started_produces_no_line(capsys) -> None:
    """Simulates a process killed while stuck inside parse_pages (stage
    3): load_pages and parse_document must have already streamed out
    (this is the real-world case a 120s timeout with zero visibility
    corresponds to), parse_pages itself gets no line (it never finished),
    and make_docx never even started."""
    handler = _StageTimingHandler(start_time=0.0)
    _fire(handler, "[1/4] Opening document...")
    capsys.readouterr()
    _fire(handler, "[2/4] Analyzing document...")
    capsys.readouterr()
    _fire(handler, "[3/4] Parsing pages...")
    captured = capsys.readouterr()
    assert "stage=parse_document" in captured.err
    assert "stage=parse_pages" not in captured.err
    assert "stage=make_docx" not in captured.err

    # The process is killed here in real life — flush_final_stage() is
    # never called (main()'s except/success paths are never reached) —
    # so no further output, and specifically no line for parse_pages
    # (still in progress) or make_docx (never started).


def test_flush_final_stage_is_a_no_op_if_no_stage_ever_started(capsys) -> None:
    handler = _StageTimingHandler(start_time=0.0)
    handler.flush_final_stage()
    assert capsys.readouterr().err == ""


def test_flush_final_stage_is_idempotent(capsys) -> None:
    handler = _StageTimingHandler(start_time=0.0)
    _fire(handler, "[4/4] Creating pages...")
    capsys.readouterr()

    handler.flush_final_stage()
    first = capsys.readouterr().err
    assert "stage=make_docx" in first

    handler.flush_final_stage()
    assert capsys.readouterr().err == ""


def test_handler_ignores_non_stage_log_records(capsys) -> None:
    handler = _StageTimingHandler(start_time=0.0)
    _fire(handler, "Start to convert /some/real/path.pdf")
    _fire(handler, "(3/10) Page 3")
    assert capsys.readouterr().err == ""
    assert handler._last_stage is None
