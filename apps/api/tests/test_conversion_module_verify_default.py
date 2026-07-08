"""`ConversionModule.verify()`'s default contract (see
app/modules/converter/base.py) — added in V2-0 Foundation as an opt-in
hook, not implemented by any real converter yet. This only guards that the
default is safe and that every one of the 17 existing converters inherits
it unchanged (none override it in this phase).
"""

from pathlib import Path

from app.modules.converter import list_converters
from app.modules.converter.base import ConversionModule, VerificationResult


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


def test_all_17_registered_converters_inherit_the_default_verify() -> None:
    converters = list_converters()
    assert len(converters) == 17
    for converter in converters:
        result = converter.verify(Path("/irrelevant.out"))
        assert result == VerificationResult(ok=True, reason=None), converter.slug
