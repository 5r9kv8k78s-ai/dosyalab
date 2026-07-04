"""Unit tests against `InMemoryOperationsEventStore` directly — bypasses
the module-level singleton (see `get_operations_event_store`) so tests
don't leak state into each other or depend on real settings.
"""

import dataclasses

from app.services.operations_events import InMemoryOperationsEventStore, classify_input_family


def test_classify_input_family_known_and_unknown_slugs() -> None:
    assert classify_input_family("pdf-to-docx") == "pdf"
    assert classify_input_family("docx-to-pdf") == "document"
    assert classify_input_family("images-to-pdf") == "image"
    assert classify_input_family("merge-pdf") == "pdf"
    assert classify_input_family(None) == "unknown"
    assert classify_input_family("some-future-tool") == "pdf"


def test_records_a_successful_conversion_event() -> None:
    store = InMemoryOperationsEventStore(max_count=100, retention_seconds=3600)

    store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="success",
        file_count=1,
        input_family="pdf",
        duration_ms=1234,
        error_code=None,
    )

    assert store.summarize_by_status() == {"success": 1}
    assert store.summarize_by_tool() == {"pdf-to-docx": 1}


def test_records_a_failed_conversion_event() -> None:
    store = InMemoryOperationsEventStore(max_count=100, retention_seconds=3600)

    store.record(
        event_type="conversion",
        tool_slug="rotate-pdf",
        status="failure",
        file_count=1,
        input_family="pdf",
        duration_ms=42,
        error_code="conversion_failed",
    )

    assert store.summarize_by_status() == {"failure": 1}
    assert store.summarize_by_error() == {"conversion_failed": 1}


def test_records_a_validation_rejected_event() -> None:
    store = InMemoryOperationsEventStore(max_count=100, retention_seconds=3600)

    store.record(
        event_type="conversion",
        tool_slug="merge-pdf",
        status="validation_rejected",
        file_count=1,
        input_family="pdf",
        duration_ms=None,
        error_code="invalid_file_count",
    )

    assert store.summarize_by_status() == {"validation_rejected": 1}
    assert store.summarize_by_error() == {"invalid_file_count": 1}


def test_records_a_rate_limit_rejection_event() -> None:
    store = InMemoryOperationsEventStore(max_count=100, retention_seconds=3600)

    store.record(
        event_type="rate_limit_rejection",
        tool_slug="merge-pdf",
        status="validation_rejected",
        file_count=0,
        input_family="pdf",
        duration_ms=None,
        error_code="rate_limited",
    )

    assert store.summarize_by_error() == {"rate_limited": 1}


def test_event_record_contains_no_filename_or_raw_ip_field() -> None:
    """The event schema itself must have no field a filename or an IP
    address could be placed in — asserted structurally, not just "we didn't
    pass one this time", so a future caller can't accidentally widen it."""
    store = InMemoryOperationsEventStore(max_count=100, retention_seconds=3600)
    store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="success",
        file_count=1,
        input_family="pdf",
        duration_ms=10,
        error_code=None,
    )

    with store._lock:
        event = store._events[0]

    field_names = {f.name for f in dataclasses.fields(event)}
    forbidden_substrings = ("filename", "file_name", "ip", "address", "path", "content", "text")
    for field_name in field_names:
        lowered = field_name.lower()
        assert not any(bad in lowered for bad in forbidden_substrings), field_name


def test_retention_prunes_by_max_count() -> None:
    store = InMemoryOperationsEventStore(max_count=3, retention_seconds=3600)

    for i in range(10):
        store.record(
            event_type="conversion",
            tool_slug=f"tool-{i}",
            status="success",
            file_count=1,
            input_family="pdf",
            duration_ms=1,
            error_code=None,
        )

    with store._lock:
        remaining = len(store._events)
    assert remaining == 3


def test_retention_prunes_by_age(monkeypatch) -> None:
    store = InMemoryOperationsEventStore(max_count=100, retention_seconds=10)

    store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="success",
        file_count=1,
        input_family="pdf",
        duration_ms=1,
        error_code=None,
    )
    assert store.summarize_by_status() == {"success": 1}

    # Simulate the retention window having fully elapsed.
    future = __import__("time").time() + 3600
    monkeypatch.setattr("app.services.operations_events.time.time", lambda: future)

    assert store.summarize_by_status() == {}
