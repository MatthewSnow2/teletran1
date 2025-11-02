"""
OpenTelemetry Instrumentation Setup.

Auto-instruments:
- FastAPI (request/response tracing)
- HTTPX (outbound HTTP calls)
- SQLAlchemy (database queries)
- Redis (cache operations)

Agent: observability-monitoring/observability-engineer
Skill: observability-monitoring/skills/distributed-tracing
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from chad_config.settings import Settings


def setup_tracing(settings: Settings) -> None:
    """
    Setup OpenTelemetry distributed tracing.

    Instruments ONLY:
    - FastAPI
    - HTTPX
    - SQLAlchemy
    - Redis

    NO AWS, NO boto3, NO unnecessary packages.

    Args:
        settings: Application settings

    TODO: Add sampling configuration for production
    TODO: Add span attributes (environment, version, etc.)
    TODO: Add Langfuse exporter integration (optional)
    """
    if not settings.OTEL_TRACES_ENABLED:
        print("⚠️  OpenTelemetry tracing disabled")
        return

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": "0.1.0",
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter (Jaeger, Tempo, etc.)
    otlp_exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)

    # Add batch span processor
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI (will be applied to app in main.py)
    # FastAPIInstrumentor().instrument()  # Applied to app instance instead

    # Auto-instrument HTTPX
    HTTPXClientInstrumentor().instrument()

    # Auto-instrument Redis
    RedisInstrumentor().instrument()

    # Auto-instrument SQLAlchemy (will instrument when engine is created)
    SQLAlchemyInstrumentor().instrument()

    print(f"✅ OpenTelemetry tracing enabled: {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
    print(f"📡 Service: {settings.OTEL_SERVICE_NAME}")


# ============================================================================
# AGENT SIGN-OFF
# ============================================================================
# ✅ observability-monitoring/observability-engineer
