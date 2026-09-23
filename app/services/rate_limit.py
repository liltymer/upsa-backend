import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

# In-memory sliding-window limiter. The API runs as a single instance on Render;
# if it is ever scaled out, move this to Redis so limits are shared.
_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    # Render (and most proxies) put the original client first in X-Forwarded-For
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, limit: int, window_seconds: int):
    """FastAPI dependency: allow `limit` requests per client IP per window."""

    def dependency(request: Request) -> None:
        key = f"{name}:{client_ip(request)}"
        now = time.monotonic()
        with _lock:
            hits = _hits[key]
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = int(window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please wait a few minutes and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    return dependency


def reset_rate_limits() -> None:
    """Used by tests."""
    with _lock:
        _hits.clear()
