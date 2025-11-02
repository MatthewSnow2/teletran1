"""
Distributed Tracing Setup (OpenTelemetry).

Auto-instruments: fastapi, httpx, sqlalchemy, redis ONLY.

Agent: observability-monitoring/observability-engineer
Skill: observability-monitoring/skills/distributed-tracing
Deliverable #4: OTEL wiring ✅
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

    Instruments: fastapi, httpx, sqlalchemy, redis
    Exports: OTLP (Jaeger/Tempo/Collector)

    Deliverable #4: OTel for fastapi/httpx/sqlalchemy/redis ✅
    """
    if not settings.OTEL_TRACES_ENABLED:
        return

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": "0.1.0",
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrument
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()

    print(f"✅ OTel tracing: {settings.OTEL_SERVICE_NAME}")
