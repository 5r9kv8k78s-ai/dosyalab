from collections.abc import Iterator
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.jobs import job_store

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PDF_PATH = FIXTURES_DIR / "sample.pdf"
SAMPLE_DOCX_PATH = FIXTURES_DIR / "sample.docx"
SAMPLE_JPG_PATH = FIXTURES_DIR / "sample.jpg"
SAMPLE_PNG_PATH = FIXTURES_DIR / "sample.png"
SAMPLE_WEBP_PATH = FIXTURES_DIR / "sample.webp"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_pdf_path() -> Path:
    return SAMPLE_PDF_PATH


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return SAMPLE_PDF_PATH.read_bytes()


@pytest.fixture
def corrupted_pdf_bytes(sample_pdf_bytes: bytes) -> bytes:
    # A real PDF's opening bytes only — not enough for PyMuPDF to recover a
    # valid xref/trailer from, so it fails to open (verified: truncating to
    # 50 bytes raises fitz.FileDataError). Derived from the real fixture, not
    # synthetic content.
    return sample_pdf_bytes[:50]


@pytest.fixture
def encrypted_pdf_bytes(sample_pdf_path: Path, tmp_path: Path) -> bytes:
    # Password-protect the real fixture document. Same real content, just
    # encrypted, to exercise the "reject encrypted PDF" path.
    doc = fitz.open(sample_pdf_path)
    output = tmp_path / "encrypted.pdf"
    doc.save(
        output,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw="user-secret",
    )
    doc.close()
    return output.read_bytes()


@pytest.fixture
def sample_docx_path() -> Path:
    return SAMPLE_DOCX_PATH


@pytest.fixture
def sample_docx_bytes() -> bytes:
    return SAMPLE_DOCX_PATH.read_bytes()


@pytest.fixture
def corrupted_docx_bytes(sample_docx_bytes: bytes) -> bytes:
    # A real DOCX's opening bytes only — not enough to form a valid ZIP
    # central directory, so python-docx fails to open it (verified:
    # truncating to 50 bytes raises zipfile.BadZipFile). Derived from the
    # real fixture, not synthetic content.
    return sample_docx_bytes[:50]


@pytest.fixture
def encrypted_docx_bytes() -> bytes:
    # Password-protected OOXML files are wrapped in an MS-CFB container and
    # start with this fixed 8-byte signature instead of the ZIP local file
    # header — see docx_validation._OLE_COMPOUND_FILE_SIGNATURE. Genuinely
    # MS-OFFCRYPTO-encrypting a real docx requires tooling this project
    # doesn't otherwise depend on (Word/LibreOffice), so this fixture tests
    # the signature-detection path directly against the real, documented
    # magic bytes rather than a full encrypted document.
    return b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100


@pytest.fixture
def sample_jpg_bytes() -> bytes:
    return SAMPLE_JPG_PATH.read_bytes()


@pytest.fixture
def sample_png_bytes() -> bytes:
    return SAMPLE_PNG_PATH.read_bytes()


@pytest.fixture
def sample_webp_bytes() -> bytes:
    return SAMPLE_WEBP_PATH.read_bytes()


@pytest.fixture
def corrupted_image_bytes(sample_jpg_bytes: bytes) -> bytes:
    # A real JPEG's opening bytes only — not enough for Pillow to decode a
    # complete image, so it fails to load (verified: truncating to 50 bytes
    # raises OSError "Truncated File Read"). Derived from the real fixture,
    # not synthetic content.
    return sample_jpg_bytes[:50]


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        # The conversion rate limiter (app/services/rate_limiter.py) keys on
        # the TestClient's fake client host, which is identical across every
        # test in the suite — without this, dozens of unrelated conversion
        # tests sharing that one key within the same 60s window would start
        # tripping 429s on each other. Rate-limit behavior itself is tested
        # separately in test_rate_limit_endpoint.py with its own Settings.
        rate_limit_enabled=False,
    )


@pytest.fixture
def client_with_tmp_storage(test_settings: Settings) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.fixture(autouse=True)
def _clear_job_store() -> Iterator[None]:
    yield
    for job in job_store.all_jobs():
        job_store.delete(job.id)
