"""Request IDs, structured access logs, and minimal Prometheus metrics."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid

from fastapi import Request, Response

logger = logging.getLogger("specrag.access")


class Metrics:
    def __init__(self) -> None:
        self.requests = 0
        self.errors = 0
        self.latency_seconds = 0.0
        self._lock = threading.Lock()

    def observe(self, status_code: int, elapsed: float) -> None:
        with self._lock:
            self.requests += 1
            self.errors += int(status_code >= 500)
            self.latency_seconds += elapsed

    def render(self) -> str:
        with self._lock:
            return "\n".join(
                [
                    "# TYPE specrag_http_requests_total counter",
                    f"specrag_http_requests_total {self.requests}",
                    "# TYPE specrag_http_errors_total counter",
                    f"specrag_http_errors_total {self.errors}",
                    "# TYPE specrag_http_latency_seconds_total counter",
                    f"specrag_http_latency_seconds_total {self.latency_seconds}",
                    "",
                ]
            )


async def request_observability(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - started
    request.app.state.metrics.observe(response.status_code, elapsed)
    response.headers["x-request-id"] = request_id
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round(elapsed * 1000, 2),
            }
        )
    )
    return response


def metrics_response(request: Request) -> Response:
    return Response(
        content=request.app.state.metrics.render(),
        media_type="text/plain; version=0.0.4",
    )
