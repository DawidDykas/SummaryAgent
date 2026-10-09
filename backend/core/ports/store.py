"""Port (interfejs) magazynu dokumentów.

Realizacja: `backend/adapters/store/memory.py` (in-memory z TTL),
dobierana przez fabrykę `backend.adapters.store.create_store()`.

Uwaga: ciała metod to świadomie puste `...` - to *kontrakt*, nie brak kodu.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from backend.core.models import StoredDocument


@runtime_checkable
class DocumentStore(Protocol):
    """Magazyn dokumentów przesłanych przez użytkownika."""

    def put(self, name: str, fmt: str, text: str, chunks: int) -> StoredDocument:
        """Zapisuje dokument i zwraca go z nadanym id."""
        ...

    def get(self, doc_id: str) -> StoredDocument | None:
        """Pobiera dokument po id; None = nie istnieje (lub wygasł TTL)."""
        ...

    def delete(self, doc_id: str) -> bool:
        """Usuwa dokument; True = istniał."""
        ...

    def cleanup(self) -> None:
        """Usuwa dokumenty, których TTL minął."""
        ...
