"""ASGI middleware: X-Request-ID + logging context + request logging."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

REQUEST_ID_HEADER = b"x-request-id"


class RequestContextMiddleware:
    """Stamp a request ID, log every HTTP request.

    Consumes X-Request-ID from the request (gateway correlation) or generates
    a new one.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = headers.get(REQUEST_ID_HEADER, b"").decode() or uuid.uuid4().hex[:12]

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (REQUEST_ID_HEADER, request_id.encode()),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            structlog.get_logger("http").info(
                "request",
                method=scope.get("method"),
                path=scope.get("path"),
                status=status_code,
                duration_ms=duration_ms,
            )
            structlog.contextvars.clear_contextvars()
