"""Lightweight, dependency-free observability: counters, request IDs, logging.

Everything lives in process memory, which suits a single-process deployment or
local development. A multi-worker setup would export these to a shared metrics
backend (e.g. Prometheus/StatsD) instead.
"""

import logging
import threading
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar
from typing import Dict

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_START = time.monotonic()


def uptime_seconds() -> float:
    return round(time.monotonic() - _START, 3)


class Counters:
    """Thread-safe monotonic counters keyed by name."""

    def __init__(self):
        self._counts = defaultdict(int)
        self._lock = threading.Lock()

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counts[name] += amount

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


counters = Counters()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] [req=%(request_id)s] %(message)s"
        )
    )
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


_logger = logging.getLogger("app.request")


async def observability_middleware(request, call_next):
    """Assign a request ID, time the request, count it and log start/end."""
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_ctx.set(rid)
    counters.increment("http.requests.total")
    start = time.monotonic()

    try:
        response = await call_next(request)
    except Exception:
        counters.increment("http.exceptions.total")
        _logger.exception(
            "request.failed method=%s path=%s", request.method, request.url.path
        )
        request_id_ctx.reset(token)
        raise

    elapsed_ms = round((time.monotonic() - start) * 1000, 2)
    counters.increment(f"http.responses.{response.status_code}")
    response.headers["X-Request-ID"] = rid
    _logger.info(
        "request method=%s path=%s status=%s ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    request_id_ctx.reset(token)
    return response
