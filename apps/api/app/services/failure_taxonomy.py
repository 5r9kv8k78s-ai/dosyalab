"""Internal failure taxonomy for `ConversionJob.error_code` (see
app/services/jobs.py) — a small, closed set of failure classes that
`run_conversion_job`'s own orchestration logic (see app/services/
conversion.py's `_classify_failure`) can genuinely distinguish today.
Never sent to the end user: the existing generic error message in
`run_conversion_job`'s outer `except Exception:` block is unchanged.

Deliberately unrelated to app/services/operations_events.py's own
`ErrorCode` Literal — that is a separate, already-closed analytics
contract feeding the Admin Panel's Errors screen (see app/db/models.py,
app/api/v1/endpoints/admin.py), and is left untouched by this module.

Only includes codes a real code path can produce as of V2-2. Candidates
considered and deliberately NOT included here (see the V2-2 report for the
full reasoning):
  - INVALID_INPUT / UNSUPPORTED_INPUT / ENCRYPTED_INPUT: these failures
    happen during `submit_*_job`, before a ConversionJob exists at all —
    there is no job to attach an error_code to without redesigning the
    submit lifecycle, which is out of scope this phase.
  - RESOURCE_LIMIT: no code path in this repository detects or raises a
    distinct resource-limit condition today.
"""

from enum import StrEnum


class FailureCode(StrEnum):
    CONVERSION_TIMEOUT = "conversion_timeout"
    ENGINE_FAILURE = "engine_failure"
    OUTPUT_MISSING = "output_missing"
    OUTPUT_INVALID = "output_invalid"
    NO_MEANINGFUL_OUTPUT = "no_meaningful_output"


# The single place a VerificationResult.reason string (see each verifier's
# own reason values in app/modules/converter/docx_to_pdf.py / pdf_to_xlsx.py)
# is translated into a FailureCode — not scattered if/elif blocks.
VERIFICATION_REASON_TO_FAILURE_CODE: dict[str, FailureCode] = {
    "output_missing": FailureCode.OUTPUT_MISSING,
    "invalid_pdf": FailureCode.OUTPUT_INVALID,
    "invalid_xlsx": FailureCode.OUTPUT_INVALID,
    "zero_pages": FailureCode.NO_MEANINGFUL_OUTPUT,
    "no_worksheets": FailureCode.NO_MEANINGFUL_OUTPUT,
}
