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

    Limits requests per actor/IP per minute.

    Features:
    - Redis-backed sliding window algorithm
    - Configurable limits per actor type
    - Rate limit headers in response
    - Exempts health check endpoints
    """

    def __init__(self, app, redis_getter=None):
        super().__init__(app)
        self.redis_getter = redis_getter
        self.exempted_paths = {"/healthz", "/readyz", "/metrics"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Exempt health checks and metrics
        if request.url.path in self.exempted_paths:
            return await call_next(request)

        # Get Redis client
        from apps.core_api.deps import get_redis_client

        redis = get_redis_client()
        if not redis:
            # If Redis unavailable, allow request (fail open)
            logger.warning("Redis not available for rate limiting, allowing request")
            return await call_next(request)

        # Determine rate limit key (IP or actor)
        # Try to extract actor from JWT if present
        actor = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from apps.core_api.auth import validate_jwt
                user = await validate_jwt(auth_header)
                actor = user.user_id
            except Exception:
                # If token invalid, fall back to IP-based rate limiting
                pass

        # Use actor if authenticated, otherwise use IP
        if actor:
            rate_limit_key = f"rate_limit:actor:{actor}"
            limit = settings.RATE_LIMIT_PER_ACTOR
        else:
            # Use client IP for anonymous requests
            client_ip = request.client.host if request.client else "unknown"
            rate_limit_key = f"rate_limit:ip:{client_ip}"
            limit = getattr(settings, "RATE_LIMIT_ANONYMOUS", 10)

        # Sliding window using Redis sorted set
        now = time.time()
        window = settings.REDIS_RATE_LIMIT_WINDOW  # seconds

        try:
            # Remove old entries (outside window)
            await redis.zremrangebyscore(rate_limit_key, 0, now - window)

            # Count requests in current window
            current_count = await redis.zcard(rate_limit_key)

            if current_count >= limit:
                # Rate limit exceeded
                # Get oldest request in window to calculate retry-after
                oldest = await redis.zrange(rate_limit_key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    retry_after = int(window - (now - oldest_time)) + 1
                else:
                    retry_after = window

                response = Response(
                    content='{"error": "rate_limit_exceeded", "message": "Too many requests"}',
                    status_code=429,
                    media_type="application/json",
                )
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(int(now + retry_after))
                return response

            # Add current request to window
            await redis.zadd(rate_limit_key, {str(uuid.uuid4()): now})
            await redis.expire(rate_limit_key, window + 10)  # Auto-cleanup

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            remaining = max(0, limit - current_count - 1)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(now + window))

            return response

        except Exception as e:
            # If rate limiting fails, allow request (fail open)
            logger.error(f"Rate limiting error: {e}", exc_info=True)
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
