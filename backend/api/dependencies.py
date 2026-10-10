"""Dependency injection (FastAPI Depends) - instead of global singletons."""

from __future__ import annotations

from fastapi import Depends, Request

from backend.adapters.extractors import extract_text
from backend.core.config import Settings, get_settings
from backend.core.ports.llm import LLMClient
from backend.core.ports.store import DocumentStore
from backend.core.services.documents import DocumentService
from backend.core.services.summary import SummaryService

__all__ = [
    "Settings",
    "get_document_service",
    "get_llm_client",
    "get_settings",
    "get_store",
    "get_summary_service",
]


def get_store(request: Request) -> DocumentStore:
    """Document store created in the application lifespan."""
    return request.app.state.store


def get_llm_client(request: Request) -> LLMClient:
    """LLM client created in the application lifespan (closed at shutdown)."""
    return request.app.state.llm_client


def get_document_service(
    settings: Settings = Depends(get_settings),
    store: DocumentStore = Depends(get_store),
) -> DocumentService:
    return DocumentService(store=store, settings=settings, extract=extract_text)


def get_summary_service(
    settings: Settings = Depends(get_settings),
    store: DocumentStore = Depends(get_store),
    client: LLMClient = Depends(get_llm_client),
) -> SummaryService:
    return SummaryService(store=store, client=client, settings=settings)
