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
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
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
