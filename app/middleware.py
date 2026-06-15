from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        clear_contextvars()

        header_correlation_id = request.headers.get("x-request-id", "").strip()
        if header_correlation_id.startswith("req-") and len(header_correlation_id) >= 8:
            correlation_id = header_correlation_id
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        bind_contextvars(correlation_id=correlation_id)
        
        request.state.correlation_id = correlation_id
        
        start = time.perf_counter()
        response = await call_next(request)

        response_time_ms = int((time.perf_counter() - start) * 1000)
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(response_time_ms)
        
        return response
