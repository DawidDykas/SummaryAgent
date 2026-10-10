"""Port (interface) for the document store.

Implementation: `backend/adapters/store/memory.py` (in-memory with TTL),
selected by the factory `backend.adapters.store.create_store()`.

Note: method bodies are intentionally empty `...` - these are *contracts*,
not missing code.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from backend.core.models import StoredDocument


@runtime_checkable
class DocumentStore(Protocol):
    """Store for documents uploaded by the user."""

    def put(self, name: str, fmt: str, text: str, chunks: int) -> StoredDocument:
        """Persist the document and return it with an assigned id."""
        ...

    def get(self, doc_id: str) -> StoredDocument | None:
        """Fetch a document by id; None if it does not exist (or TTL expired)."""
        ...

    def delete(self, doc_id: str) -> bool:
        """Delete a document; True if it existed."""
        ...

    def cleanup(self) -> None:
        """Remove documents whose TTL has expired."""
        ...
