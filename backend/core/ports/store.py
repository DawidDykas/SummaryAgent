"""Port magazynu dokumentów - implementacje żyją w backend.adapters.store."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from backend.core.models import StoredDocument


@runtime_checkable
class DocumentStore(Protocol):
    def put(self, name: str, fmt: str, text: str, chunks: int) -> StoredDocument: ...

    def get(self, doc_id: str) -> StoredDocument | None: ...

    def delete(self, doc_id: str) -> bool: ...

    def cleanup(self) -> None: ...
