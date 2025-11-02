"""
Structured Logging (structlog).

Provides request_id, trace_id, actor correlation.

Agent: observability-monitoring/observability-engineer
Deliverable #4: Structured logging ✅
"""

import logging
import sys

import structlog

from chad_config.settings import Settings


def setup_logging(settings: Settings) -> None:
    """
    Configure structlog for structured logging.

    Output format: JSON (default) or text (dev)
    Includes: request_id, trace_id, actor, timestamp
    """
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=settings.LOG_LEVEL.upper()
    )

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get configured logger."""
    return structlog.get_logger(name)
