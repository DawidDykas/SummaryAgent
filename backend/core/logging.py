"""Konfiguracja logowania (structlog) - wywoływana raz przy starcie aplikacji."""

from __future__ import annotations

import logging

import structlog

from backend.core.config import Settings


def setup_logging(settings: Settings) -> None:
    """Konfiguruje structlog: JSON w produkcji, czytelna konsola w dev."""
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

    # force=True czyści handler roota (uwaga: logi uvicorn mają własne
    # handlery na loggerach "uvicorn.*", więc nie tracimy ich formatowania)
    logging.basicConfig(level=settings.log_level, format="%(message)s", force=True)

    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
