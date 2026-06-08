"""API-key authentication and in-memory rate limiting.

Both features are opt-in via settings so the demo runs open by default:
- ``api_keys`` empty  -> no authentication (anonymous access)
- ``rate_limit_per_minute`` <= 0 -> no rate limiting

When enabled, the dependency raises a structured 401 (auth) or 429 (rate
limit) with the appropriate headers.
"""

import hashlib
import threading
import time
from collections import defaultdict, deque
from typing import Optional, Tuple

from fastapi import Header, HTTPException, Request, status

from app.config import get_settings

ANONYMOUS_IDENTITY = "anonymous"


class RateLimiter:
    """Sliding-window rate limiter keyed by identity, held in process memory.

    Suitable for a single-process deployment or local development. A multi-
    worker deployment would back this with a shared store such as Redis.
    """

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def check(self, identity: str, limit: int, window: float = 60.0) -> Tuple[bool, int]:
        """Record a hit and report whether it is allowed.

        Returns ``(allowed, retry_after_seconds)``. When ``limit`` is non-
        positive the limiter is disabled and every call is allowed.
        """
        if limit <= 0:
            return True, 0

        now = time.monotonic()
        with self._lock:
            hits = self._hits[identity]
            cutoff = now - window
            while hits and hits[0] <= cutoff:
                hits.popleft()

            if len(hits) >= limit:
                # Oldest hit leaves the window after this many seconds; round up
                # so a sub-second wait still yields a usable integer.
                retry_after = max(1, int(window - (now - hits[0])) + 1)
                return False, retry_after

            hits.append(now)
            return True, 0


rate_limiter = RateLimiter()


def _allowed_keys() -> set:
    raw = get_settings().api_keys
    return {key.strip() for key in raw.split(",") if key.strip()}


def _identity_for(key: Optional[str], request: Request) -> str:
    if key:
        # Hash so the raw key never lands in logs or the limiter's key space.
        return "key:" + hashlib.sha256(key.encode()).hexdigest()[:16]
    client = request.client
    return f"ip:{client.host}" if client else ANONYMOUS_IDENTITY


async def require_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> str:
    """Authenticate (when keys are configured) and charge one rate-limit token.

    Returns the caller's identity so handlers can log it. Raises 401 for a
    missing/invalid key or 429 when the per-identity limit is exceeded.
    """
    settings = get_settings()
    keys = _allowed_keys()

    if keys and (x_api_key is None or x_api_key not in keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthenticated",
                "message": "A valid X-API-Key header is required",
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

    identity = _identity_for(x_api_key, request)
    allowed, retry_after = rate_limiter.check(
        identity,
        settings.rate_limit_per_minute,
        settings.rate_limit_window_seconds,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limited",
                "limit_per_minute": settings.rate_limit_per_minute,
                "retry_after_seconds": retry_after,
                "message": "Rate limit exceeded; slow down",
            },
            headers={"Retry-After": str(retry_after)},
        )
    return identity
