"""Public-production abuse protection for the conversion/upload surface.

This is V1 abuse mitigation, not DDoS protection — it slows down a single
misbehaving client, it does not defend against a distributed attack or
absorb large traffic volume. See `FixedWindowRateLimiter`'s docstring for
its specific, honestly-stated limitations.
"""

import logging
import threading
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request

from app.core.config import Settings, get_settings
from app.services.operations_events import classify_input_family, record_operations_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int | None


class FixedWindowRateLimiter:
    """Process-local, fixed-window rate limiter keyed by an arbitrary
    string (the caller's resolved client host, for conversion routes).

    LIMITATIONS — read before relying on this in production:

    - Process-local only: counters live in this process's memory, not a
      shared store. If the API ever runs more than one replica, each
      replica enforces its own independent limit — a client could reach
      `max_requests` PER REPLICA, not per deployment. A future Redis-backed
      implementation (e.g. `INCR` + `EXPIRE`) can satisfy the same
      `check(key)` interface without changing any route or dependency.
    - Resets on restart: every counter is lost when the process restarts.
    - Fixed window, not sliding: a client can send `max_requests` right at
      the end of one window and another `max_requests` right at the start
      of the next — up to ~2x `max_requests` in a short burst straddling a
      window boundary. Accepted V1 tradeoff; a token-bucket/sliding-window
      algorithm would smooth this out but isn't justified for a lightweight
      V1 abuse guard.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        # key -> (window_index, count_in_that_window)
        self._counts: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> RateLimitResult:
        now = time.time()
        window_index = int(now // self._window_seconds)
        window_end = (window_index + 1) * self._window_seconds
        retry_after_seconds = max(1, int(window_end - now))

        with self._lock:
            self._prune_stale_windows_locked(window_index)
            stored_window, count = self._counts.get(key, (window_index, 0))
            if stored_window != window_index:
                stored_window, count = window_index, 0
            count += 1
            self._counts[key] = (stored_window, count)
            allowed = count <= self._max_requests

        return RateLimitResult(
            allowed=allowed,
            retry_after_seconds=None if allowed else retry_after_seconds,
        )

    def _prune_stale_windows_locked(self, current_window: int) -> None:
        # Opportunistic prune of keys from past windows on every check —
        # bounds memory to "distinct clients seen in the current window"
        # without a background scheduler, mirroring the retention pruning
        # in app/services/operations_events.py.
        stale_keys = [key for key, (window, _) in self._counts.items() if window < current_window]
        for key in stale_keys:
            del self._counts[key]


_conversion_limiter: FixedWindowRateLimiter | None = None
_conversion_limiter_lock = threading.Lock()


def _get_conversion_limiter(settings: Settings) -> FixedWindowRateLimiter:
    global _conversion_limiter
    if _conversion_limiter is None:
        with _conversion_limiter_lock:
            if _conversion_limiter is None:
                _conversion_limiter = FixedWindowRateLimiter(
                    max_requests=settings.rate_limit_requests,
                    window_seconds=settings.rate_limit_window_seconds,
                )
    return _conversion_limiter


def _client_key(request: Request) -> str:
    """The ASGI server's own resolved client host — never a raw
    `X-Forwarded-For` header read directly, which any client can set to an
    arbitrary value. If DosyaLab is deployed behind a reverse proxy/load
    balancer, run uvicorn with `--proxy-headers
    --forwarded-allow-ips=<proxy IP>` so `request.client.host` is safely
    resolved from a trusted `X-Forwarded-For` entry instead of the proxy's
    own address — that is uvicorn's own trusted-proxy mechanism, not
    something reimplemented here. Without those flags (the default), this
    is simply the raw TCP peer address, which is safe but will be the
    load balancer's address for every request behind an unconfigured proxy.
    """
    if request.client is None:
        return "unknown"
    return request.client.host


async def enforce_conversion_rate_limit(
    request: Request, settings: Settings = Depends(get_settings)
) -> None:
    """FastAPI dependency wired onto every conversion/upload route (see
    `dependencies=[Depends(enforce_conversion_rate_limit)]` in convert.py) —
    not onto health, robots, sitemap, or static asset routes, since those
    aren't the expensive operation this protects.
    """
    if not settings.rate_limit_enabled:
        return

    limiter = _get_conversion_limiter(settings)
    result = limiter.check(_client_key(request))
    if result.allowed:
        return

    # The URL path segment after the last "/" is the tool slug for every
    # /api/v1/convert/{slug} route — reliable without threading the literal
    # slug string through this shared dependency. The client's identifier is
    # used only to enforce the limit above; it is never copied into the
    # long-lived operations event below.
    tool_slug = request.url.path.rsplit("/", 1)[-1]
    record_operations_event(
        event_type="rate_limit_rejection",
        tool_slug=tool_slug,
        status="validation_rejected",
        file_count=0,
        input_family=classify_input_family(tool_slug),
        duration_ms=None,
        error_code="rate_limited",
    )
    logger.warning("rate_limit.rejected", extra={"tool_slug": tool_slug})
    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please slow down and try again shortly.",
        headers={"Retry-After": str(result.retry_after_seconds)},
    )
