"""`ConversionModule.verify()`'s default contract (see
app/modules/converter/base.py) — added in V2-0 Foundation as an opt-in
hook, not implemented by any real converter yet at the time. This guards
that the default itself is still unconditionally safe (ok=True), and that
every registered converter still either inherits it unchanged or (as of
V2-1, for docx-to-pdf and pdf-to-xlsx only — see test_docx_to_pdf_verify.py
/ test_pdf_to_xlsx_verify.py) overrides it with a real check.
"""

from pathlib import Path

from app.modules.converter import list_converters
from app.modules.converter.base import ConversionModule, VerificationResult

# V2-1 gave these two tools a real verify() override (see
# app/modules/converter/docx_to_pdf.py / pdf_to_xlsx.py) — both correctly
# reject a nonexistent output path, unlike the other 15 which still inherit
# the unconditional ok=True default.
_TOOLS_WITH_REAL_VERIFIERS = {"docx-to-pdf", "pdf-to-xlsx"}


class _MinimalConverter(ConversionModule):
    slug = "minimal-test-tool"
    input_formats = ("pdf",)
    output_format = "pdf"

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        return destination_dir / "out.pdf"


def test_default_verify_returns_ok_true() -> None:
    result = _MinimalConverter().verify(Path("/nonexistent/does-not-matter.pdf"))
    assert result == VerificationResult(ok=True, reason=None)


def test_default_verify_ok_true_regardless_of_output_path_existing() -> None:
    # Deliberately doesn't check the filesystem at all in this phase — a
    # converter that wants a real check opts in by overriding verify().
    result = _MinimalConverter().verify(Path("/definitely/does/not/exist.pdf"))
    assert result.ok is True


def test_15_of_17_registered_converters_still_inherit_the_default_verify() -> None:
    converters = list_converters()
    assert len(converters) == 17
    for converter in converters:
        if converter.slug in _TOOLS_WITH_REAL_VERIFIERS:
            continue
        result = converter.verify(Path("/irrelevant.out"))
        assert result == VerificationResult(ok=True, reason=None), converter.slug


def test_exactly_the_expected_two_tools_have_a_real_verifier() -> None:
    """A converter overriding verify() must be a deliberate decision, not an
    accident — this fails loudly if a future change silently overrides
    verify() on a tool not yet covered by its own dedicated verifier tests."""
    converters = list_converters()
    overriding_slugs = {
        converter.slug
        for converter in converters
        if type(converter).verify is not ConversionModule.verify
    }
    assert overriding_slugs == _TOOLS_WITH_REAL_VERIFIERS
