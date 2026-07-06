"""Exercises PostgresOperationsEventStore/PostgresFeedbackStore against a
real SQLite database (file-backed, one per test) rather than a live
Postgres instance — the actual production target is Postgres (see
DATABASE_URL in .env.example), but the query layer (SQLAlchemy Core/ORM)
is portable, and this is the correct test-double boundary: it exercises
the real store classes and real SQL execution, not a hand-rolled fake.

A real Postgres integration run is out of this sandbox's reach (no
Postgres instance available) — see the test report for what that means.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import Base
from app.services.operations_events import PostgresOperationsEventStore
from app.services.feedback import PostgresFeedbackStore
from app.services.site_settings import PostgresSiteSettingsStore


@pytest.fixture
def sqlite_engine(tmp_path, monkeypatch):
    from sqlalchemy import create_engine

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    import app.db.session as session_module

    monkeypatch.setattr(session_module, "_engine", engine)
    monkeypatch.setattr(
        session_module, "_session_factory", session_module.sessionmaker(bind=engine, future=True)
    )
    return engine


def test_operations_event_store_records_and_summarizes(sqlite_engine) -> None:
    store = PostgresOperationsEventStore()
    store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="success",
        file_count=1,
        input_family="pdf",
        duration_ms=1200,
        error_code=None,
    )
    store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="failure",
        file_count=1,
        input_family="pdf",
        duration_ms=400,
        error_code="conversion_failed",
    )

    assert store.summarize_by_status() == {"success": 1, "failure": 1}
    assert store.summarize_by_tool() == {"pdf-to-docx": 2}
    assert store.summarize_by_error() == {"conversion_failed": 1}


def test_overview_success_rate_and_zero_data(sqlite_engine) -> None:
    store = PostgresOperationsEventStore()
    since = datetime.now(UTC) - timedelta(days=7)

    # Zero-data behavior: no divide-by-zero, sensible defaults.
    empty = store.get_overview(since)
    assert empty.conversion_attempts == 0
    assert empty.success_rate == 0.0
    assert empty.average_duration_ms is None
    assert empty.total_files_processed == 0

    store.record(
        event_type="conversion",
        tool_slug="merge-pdf",
        status="success",
        file_count=3,
        input_family="pdf",
        duration_ms=800,
        error_code=None,
    )
    store.record(
        event_type="conversion",
        tool_slug="merge-pdf",
        status="failure",
        file_count=2,
        input_family="pdf",
        duration_ms=200,
        error_code="conversion_failed",
    )
    store.record(
        event_type="conversion",
        tool_slug="images-to-pdf",
        status="validation_rejected",
        file_count=0,
        input_family="image",
        duration_ms=None,
        error_code="invalid_file_type",
    )
    store.record(
        event_type="rate_limit_rejection",
        tool_slug="merge-pdf",
        status="validation_rejected",
        file_count=0,
        input_family="pdf",
        duration_ms=None,
        error_code="rate_limited",
    )

    metrics = store.get_overview(since)
    assert metrics.conversion_attempts == 3
    assert metrics.successful_conversions == 1
    assert metrics.failed_conversions == 1
    assert metrics.validation_rejections == 1
    assert metrics.rate_limit_rejections == 1
    assert metrics.success_rate == pytest.approx(1 / 3)
    assert metrics.average_duration_ms == pytest.approx(500.0)  # (800 + 200) / 2
    assert metrics.total_files_processed == 3  # only the successful job's file_count


def test_overview_respects_date_range(sqlite_engine) -> None:
    from app.db.session import session_scope
    from app.db.models import OperationsEventRow
    import uuid

    store = PostgresOperationsEventStore()
    old_time = datetime.now(UTC) - timedelta(days=30)
    with session_scope() as session:
        session.add(
            OperationsEventRow(
                event_id=uuid.uuid4().hex,
                event_type="conversion",
                tool_slug="pdf-to-docx",
                status="success",
                file_count=1,
                input_family="pdf",
                duration_ms=100,
                error_code=None,
                created_at=old_time,
            )
        )

    recent_since = datetime.now(UTC) - timedelta(days=7)
    assert store.get_overview(recent_since).conversion_attempts == 0
    old_since = datetime.now(UTC) - timedelta(days=60)
    assert store.get_overview(old_since).conversion_attempts == 1


def test_tool_aggregation(sqlite_engine) -> None:
    store = PostgresOperationsEventStore()
    since = datetime.now(UTC) - timedelta(days=7)
    for _ in range(3):
        store.record(
            event_type="conversion",
            tool_slug="pdf-to-docx",
            status="success",
            file_count=1,
            input_family="pdf",
            duration_ms=100,
            error_code=None,
        )
    store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="failure",
        file_count=1,
        input_family="pdf",
        duration_ms=50,
        error_code="conversion_failed",
    )

    tools = store.get_tool_aggregation(since)
    assert len(tools) == 1
    assert tools[0].tool_slug == "pdf-to-docx"
    assert tools[0].attempt_count == 4
    assert tools[0].success_count == 3
    assert tools[0].failure_count == 1
    assert tools[0].success_rate == pytest.approx(0.75)


def test_error_aggregation(sqlite_engine) -> None:
    store = PostgresOperationsEventStore()
    since = datetime.now(UTC) - timedelta(days=7)
    store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="validation_rejected",
        file_count=1,
        input_family="pdf",
        duration_ms=None,
        error_code="invalid_file_type",
    )
    store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="validation_rejected",
        file_count=1,
        input_family="pdf",
        duration_ms=None,
        error_code="invalid_file_type",
    )

    errors = store.get_error_aggregation(since)
    assert errors == [("invalid_file_type", 2)]


def test_operations_event_row_has_no_filename_or_ip_column() -> None:
    from app.db.models import OperationsEventRow

    column_names = {column.name for column in OperationsEventRow.__table__.columns}
    forbidden = ("filename", "file_name", "ip", "ip_address", "user_agent", "path", "content")
    for name in column_names:
        lowered = name.lower()
        assert not any(bad in lowered for bad in forbidden), name


def test_feedback_store_create_list_and_update_status(sqlite_engine) -> None:
    store = PostgresFeedbackStore()
    created = store.create(category="idea", message="Bir öneri paylaşmak istiyorum.", email=None)
    assert created.status == "new"

    items = store.list(status=None, category=None)
    assert len(items) == 1
    assert items[0].feedback_id == created.feedback_id

    updated = store.update_status(created.feedback_id, "reviewing")
    assert updated is not None
    assert updated.status == "reviewing"

    missing = store.update_status("does-not-exist", "reviewing")
    assert missing is None


def test_feedback_row_has_no_ip_or_user_agent_column() -> None:
    from app.db.models import FeedbackRow

    column_names = {column.name for column in FeedbackRow.__table__.columns}
    forbidden = ("ip", "ip_address", "user_agent", "filename")
    for name in column_names:
        lowered = name.lower()
        assert not any(bad in lowered for bad in forbidden), name


def test_operations_event_clear_all_deletes_events_only(sqlite_engine) -> None:
    events_store = PostgresOperationsEventStore()
    feedback_store = PostgresFeedbackStore()

    events_store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="success",
        file_count=1,
        input_family="pdf",
        duration_ms=100,
        error_code=None,
    )
    events_store.record(
        event_type="conversion",
        tool_slug="pdf-to-docx",
        status="failure",
        file_count=1,
        input_family="pdf",
        duration_ms=50,
        error_code="conversion_failed",
    )
    feedback_store.create(category="idea", message="Bu kalsın lütfen.", email=None)

    deleted_count = events_store.clear_all()

    assert deleted_count == 2
    since = datetime.now(UTC) - timedelta(days=1)
    assert events_store.get_overview(since).conversion_attempts == 0
    # Feedback must survive an operations-history clear untouched.
    assert len(feedback_store.list(status=None, category=None)) == 1


def test_operations_event_clear_all_on_empty_store_returns_zero(sqlite_engine) -> None:
    store = PostgresOperationsEventStore()
    assert store.clear_all() == 0


def test_site_settings_store_defaults_to_disabled_when_row_missing(sqlite_engine) -> None:
    store = PostgresSiteSettingsStore()
    status = store.get_maintenance_status()
    assert status.enabled is False


def test_site_settings_store_set_and_get_round_trips(sqlite_engine) -> None:
    store = PostgresSiteSettingsStore()

    enabled_status = store.set_maintenance_status(enabled=True, message="Bakımdayız.")
    assert enabled_status.enabled is True
    assert enabled_status.message == "Bakımdayız."

    # A fresh store instance (simulating a new request/process) must read
    # back the same state — this is the actual "survives a restart"
    # guarantee, since nothing here is held in process memory.
    reloaded = PostgresSiteSettingsStore()
    assert reloaded.get_maintenance_status() == enabled_status

    disabled_status = store.set_maintenance_status(enabled=False, message="Bakımdayız.")
    assert disabled_status.enabled is False
    assert PostgresSiteSettingsStore().get_maintenance_status().enabled is False


def test_site_settings_row_is_a_true_singleton() -> None:
    from app.db.models import SiteSettingsRow

    constraint_names = {c.name for c in SiteSettingsRow.__table__.constraints}
    assert "ck_site_settings_singleton" in constraint_names
