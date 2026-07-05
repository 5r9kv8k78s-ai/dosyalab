"""Database engine/session management for the Postgres-backed persistence
layer. Sync SQLAlchemy (not async) — every call site runs the blocking
query inside `asyncio.to_thread`, the same pattern `run_conversion_job`
already uses for blocking conversion work, rather than adopting a second,
async-native database stack for a handful of read/write queries.
"""

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when `OPERATIONS_STORE_BACKEND=postgres` but `DATABASE_URL`
    is missing. Fails loudly at first use rather than silently falling
    back to in-memory storage — persistence that quietly isn't persistent
    is worse than a startup error."""


_engine: Engine | None = None
_engine_lock = threading.Lock()
_session_factory: sessionmaker[Session] | None = None


def _with_psycopg_driver(database_url: str) -> str:
    """This project depends on `psycopg` (v3, see requirements.txt) rather
    than `psycopg2` — but a bare `postgresql://`/`postgres://` URL (e.g.
    pasted directly from Supabase's "Connection string (URI)" dashboard
    field, which never includes a driver suffix) makes SQLAlchemy default
    to the psycopg2 dialect regardless, which isn't installed. Force the
    psycopg3 dialect explicitly so the driver actually used matches the
    one actually installed, no matter how the URL was written."""
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://") :]
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://") :]
    return database_url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                settings = get_settings()
                if not settings.database_url:
                    raise DatabaseNotConfiguredError(
                        "DATABASE_URL is required when OPERATIONS_STORE_BACKEND=postgres."
                    )
                url = _with_psycopg_driver(settings.database_url)
                # Without this, a stalled/unreachable Postgres host has no
                # bound on how long a *connection attempt* can hang (verified
                # against the real Supabase instance: psycopg accepts this
                # via connect_args, same as plain libpq's connect_timeout).
                # This only bounds establishing the connection, not query
                # execution time — pairs with running every caller's write
                # in a worker thread (see run_conversion_job) so a slow
                # query still can't block the event loop either way.
                _engine = create_engine(
                    url, pool_pre_ping=True, future=True, connect_args={"connect_timeout": 10}
                )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False, future=True
        )
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """One transaction per call — commits on success, rolls back and
    re-raises on any exception, always closes."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
