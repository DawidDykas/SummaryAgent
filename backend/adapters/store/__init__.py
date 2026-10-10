"""Document store factory."""

from __future__ import annotations

from backend.core.config import Settings
from backend.core.ports.store import DocumentStore

from .memory import InMemoryDocumentStore

__all__ = ["DocumentStore", "InMemoryDocumentStore", "create_store"]


def create_store(settings: Settings) -> DocumentStore:
    """In-memory store by default; add further implementations here (Redis, DB)."""
    return InMemoryDocumentStore(ttl_seconds=settings.doc_ttl_seconds)
