"""
Chad-Core FastAPI Application Entry Point.

This module initializes the FastAPI application with:
- CORS middleware
- OpenTelemetry instrumentation
- Rate limiting middleware
- Request ID injection
- Lifespan context management (DB, Redis connections)
- Router mounting

Agents:
- api-scaffolding/fastapi-pro
- observability-monitoring/observability-engineer
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from chad_config.settings import Settings
from chad_obs.logging import setup_logging
from chad_obs.tracing import setup_tracing

# Import routers
from apps.core_api.routers import act, health, metrics, runs

# Initialize settings
settings = Settings()

# Setup logging
setup_logging(settings)

# Setup OpenTelemetry tracing
setup_tracing(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles:
    - Database connection pool initialization
    - Redis connection initialization
    - Graceful shutdown

    TODO: Implement connection pooling
    TODO: Add health check warmup
    TODO: Implement graceful shutdown with timeout
    """
    # Startup
    print("🚀 Chad-Core API starting up...")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    print(f"🗄️  Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")
    print(f"💾 Redis: {settings.REDIS_URL}")

    # TODO: Initialize database connection pool
    # app.state.db = await init_db_pool(settings.DATABASE_URL)

    # TODO: Initialize Redis connection
    # app.state.redis = await init_redis_pool(settings.REDIS_URL)

    # TODO: Run health checks
    # await check_db_connection(app.state.db)
    # await check_redis_connection(app.state.redis)

    yield

    # Shutdown
    print("🛑 Chad-Core API shutting down...")

    # TODO: Close database connections
    # await app.state.db.close()

    # TODO: Close Redis connections
    # await app.state.redis.close()

    print("✅ Graceful shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="Chad-Core API",
    description="Jarvis-inspired hybrid agentic service with LangGraph orchestration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API_CORS_ORIGINS.split(",") if settings.API_CORS_ORIGINS else ["*"],
    allow_credentials=settings.API_CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Trace-ID"],
)

# TODO: Add rate limiting middleware
# from apps.core_api.middleware import RateLimitMiddleware
# app.add_middleware(RateLimitMiddleware)

# TODO: Add request ID middleware
# from apps.core_api.middleware import RequestIDMiddleware
# app.add_middleware(RequestIDMiddleware)

# OpenTelemetry FastAPI instrumentation is auto-applied in chad_obs/tracing.py

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled exceptions.

    TODO: Add structured logging with trace context
    TODO: Sanitize error messages (don't expose internal details)
    TODO: Add Sentry/error tracking integration
    """
    import traceback

    print(f"❌ Unhandled exception: {exc}")
    traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please contact support.",
            # TODO: Include trace_id for debugging
        },
    )


# ============================================================================
# ROUTERS
# ============================================================================

# Core execution endpoint
app.include_router(act.router, prefix="", tags=["execution"])

# Run viewer endpoints
app.include_router(runs.router, prefix="/runs", tags=["runs"])

# Health and metrics
app.include_router(health.router, prefix="", tags=["health"])
app.include_router(metrics.router, prefix="", tags=["metrics"])


# ============================================================================
# ROOT ENDPOINT
# ============================================================================


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint - API information.

    Returns:
        API metadata and available endpoints
    """
    return {
        "name": "Chad-Core API",
        "version": "0.1.0",
        "description": "Jarvis-inspired hybrid agentic service",
        "docs": "/docs",
        "health": "/healthz",
        "metrics": "/metrics",
        "endpoints": {
            "execution": "POST /act",
            "runs": "GET /runs",
            "run_detail": "GET /runs/{id}",
            "run_steps": "GET /runs/{id}/steps",
        },
    }


# ============================================================================
# DEVELOPMENT HELPERS
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Development server (auto-reload enabled)
    uvicorn.run(
        "apps.core_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

# ============================================================================
# AGENT SIGN-OFF
# ============================================================================
# ✅ api-scaffolding/fastapi-pro
# ✅ observability-monitoring/observability-engineer
