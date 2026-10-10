"""Logging setup (structlog) - called once at application startup."""

from __future__ import annotations

import logging

import structlog

from backend.core.config import Settings


def setup_logging(settings: Settings) -> None:
    """Configure structlog: JSON in production, readable console in dev."""
    shared: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer = (
        structlog.processors.JSONRenderer() if settings.log_json else structlog.dev.ConsoleRenderer()
    )

    # force=True clears the root handler (note: uvicorn logs use their own
    # handlers on "uvicorn.*" loggers, so their formatting is preserved)
    logging.basicConfig(level=settings.log_level, format="%(message)s", force=True)

    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
