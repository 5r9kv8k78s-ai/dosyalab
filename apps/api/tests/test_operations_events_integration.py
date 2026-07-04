"""End-to-end checks that real requests through the FastAPI app produce the
expected operations events — and, critically, that those events never carry
a filename or a raw IP address. `app.services.operations_events` builds its
store as a module-level singleton, so each test resets it first.
"""

import io

import app.services.operations_events as operations_events_module
from fastapi.testclient import TestClient

from app.core.config import get_settings


def _reset_store() -> None:
    operations_events_module._store = None


def test_successful_conversion_records_a_success_event(
    client_with_tmp_storage: TestClient, sample_pdf_bytes: bytes
) -> None:
    _reset_store()
    response = client_with_tmp_storage.post(
        "/api/v1/convert/pdf-to-docx",
        files=[("file", ("my-secret-report.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
    )
    assert response.status_code == 202

    store = operations_events_module.get_operations_event_store()
    assert store.summarize_by_status().get("success") == 1
    assert store.summarize_by_tool().get("pdf-to-docx") == 1

    with store._lock:
        events = list(store._events)
    assert len(events) == 1
    event = events[0]
    assert event.duration_ms is not None and event.duration_ms >= 0
    assert event.input_family == "pdf"
    # The literal filename must never appear anywhere in the recorded event.
    event_repr = repr(event)
    assert "my-secret-report" in "my-secret-report.pdf"  # sanity: filename we uploaded
    assert "my-secret-report" not in event_repr


def test_validation_rejection_records_event_with_stable_error_code(
    client_with_tmp_storage: TestClient,
) -> None:
    _reset_store()
    response = client_with_tmp_storage.post(
        "/api/v1/convert/pdf-to-docx",
        files=[("file", ("notes.txt", io.BytesIO(b"not a pdf"), "text/plain"))],
    )
    assert response.status_code == 400

    store = operations_events_module.get_operations_event_store()
    assert store.summarize_by_status().get("validation_rejected") == 1
    assert store.summarize_by_error().get("invalid_file_type") == 1

    with store._lock:
        events = list(store._events)
    event_repr = repr(events[0])
    assert "notes.txt" not in event_repr


def test_operations_events_disabled_setting_records_nothing(
    tmp_path, sample_pdf_bytes: bytes
) -> None:
    from app.core.config import Settings
    from app.main import app

    # Reset first: this store singleton is shared across every test in this
    # file (see module docstring) — without this, a real event recorded by
    # an earlier test in this same file/run would still be sitting in the
    # store when this test makes its assertion below, even though nothing
    # was recorded by *this* test's own (disabled) request.
    _reset_store()
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        convert_upload_dir=tmp_path / "convert" / "uploads",
        convert_output_dir=tmp_path / "convert" / "outputs",
        operations_events_enabled=False,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/convert/pdf-to-docx",
                files=[("file", ("doc.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
            )
            assert response.status_code == 202
    finally:
        app.dependency_overrides.pop(get_settings, None)

    # get_operations_event_store() itself reads the *real* cached settings
    # (operations_events_enabled defaults to True), independent of this
    # request's overridden settings — so nothing was recorded because
    # record_operations_event's own settings.operations_events_enabled
    # check (evaluated with the overridden settings inside the request)
    # short-circuited before ever touching the store.
    store = operations_events_module.get_operations_event_store()
    assert store.summarize_by_status() == {}
