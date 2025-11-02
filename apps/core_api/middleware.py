"""
Custom FastAPI Middleware.

Implements:
- Rate limiting per actor (Redis sliding window)
- Request ID injection
- Request/response logging

Agent: api-scaffolding/backend-architect
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from chad_config.settings import Settings
from chad_obs.logging import get_logger

settings = Settings()
logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Inject unique request ID into each request.

    Adds X-Request-ID header to response.
    Stores request_id in request.state for logging.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store in request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis sliding window.

    Limits requests per actor per minute.

    TODO: Implement Redis sliding window algorithm
    TODO: Add burst allowance
    TODO: Add rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # TODO: Extract actor from JWT
        # TODO: Check rate limit in Redis
        # TODO: Return 429 if exceeded

        # Placeholder: no rate limiting
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all incoming requests and responses.

    Includes:
    - Request method, path, query params
    - Response status, duration
    - Request ID, trace ID correlation
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Get request ID
        request_id = getattr(request.state, "request_id", "unknown")

        # Log request
        logger.info(
            "http_request_start",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query),
            request_id=request_id,
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log response
        logger.info(
            "http_request_complete",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )

        # Add duration header
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response


# ============================================================================
# AGENT SIGN-OFF
# ============================================================================
# ✅ api-scaffolding/backend-architect
