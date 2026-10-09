"""Wstrzykiwanie zależności (FastAPI Depends) - zamiast globalnych singletonów."""

from __future__ import annotations

from fastapi import Request

from backend.core.config import Settings, get_settings
from backend.core.ports.llm import LLMClient
from backend.core.ports.store import DocumentStore

__all__ = ["Settings", "get_llm_client", "get_settings", "get_store"]


def get_store(request: Request) -> DocumentStore:
    """Magazyn dokumentów utworzony w lifespanie aplikacji."""
    return request.app.state.store


def get_llm_client(request: Request) -> LLMClient:
    """Klient LLM utworzony w lifespanie aplikacji (zamykany przy shutdown)."""
    return request.app.state.llm_client
