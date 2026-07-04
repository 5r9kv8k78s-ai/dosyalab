"""Unit tests against `FixedWindowRateLimiter` directly — not through the
FastAPI app — since the conversion routes' limiter is a module-level
singleton (see app/services/rate_limiter.py's `_get_conversion_limiter`)
that would otherwise leak state between test functions in the same process.
"""

from app.services.rate_limiter import FixedWindowRateLimiter


def test_allows_requests_below_threshold() -> None:
    limiter = FixedWindowRateLimiter(max_requests=3, window_seconds=60)

    for _ in range(3):
        result = limiter.check("client-a")
        assert result.allowed is True
        assert result.retry_after_seconds is None


def test_blocks_requests_above_threshold() -> None:
    limiter = FixedWindowRateLimiter(max_requests=2, window_seconds=60)

    assert limiter.check("client-a").allowed is True
    assert limiter.check("client-a").allowed is True
    third = limiter.check("client-a")
    assert third.allowed is False
    assert third.retry_after_seconds is not None
    assert third.retry_after_seconds > 0


def test_retry_after_is_within_the_window(monkeypatch) -> None:
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=30)

    # Pin `time.time()` to a known instant so the window boundary (and thus
    # the expected Retry-After) is deterministic rather than depending on
    # when the test happens to run relative to a 30s wall-clock boundary.
    monkeypatch.setattr("app.services.rate_limiter.time.time", lambda: 100.0)

    assert limiter.check("client-a").allowed is True
    blocked = limiter.check("client-a")
    assert blocked.allowed is False
    # Window index for t=100, window=30 is 3 (90-120); retry-after = 120-100 = 20.
    assert blocked.retry_after_seconds == 20


def test_different_keys_are_isolated() -> None:
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60)

    assert limiter.check("client-a").allowed is True
    # client-a is now over its limit, but client-b has made no requests yet.
    assert limiter.check("client-a").allowed is False
    assert limiter.check("client-b").allowed is True


def test_limit_resets_in_a_new_window(monkeypatch) -> None:
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=10)

    current_time = 100.0
    monkeypatch.setattr("app.services.rate_limiter.time.time", lambda: current_time)

    assert limiter.check("client-a").allowed is True
    assert limiter.check("client-a").allowed is False

    # Advance past the current 10s window into the next one.
    current_time = 111.0
    assert limiter.check("client-a").allowed is True
