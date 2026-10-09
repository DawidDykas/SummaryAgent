"""Magazyn dokumentów w pamięci procesu (z TTL) - domyślna implementacja portu."""

from __future__ import annotations

import time

from backend.core.models import StoredDocument


class InMemoryDocumentStore:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._docs: dict[str, StoredDocument] = {}

    def put(self, name: str, fmt: str, text: str, chunks: int) -> StoredDocument:
        self.cleanup()
        doc = StoredDocument.create(name=name, fmt=fmt, text=text, chunks=chunks)
        self._docs[doc.id] = doc
        return doc

    def get(self, doc_id: str) -> StoredDocument | None:
        self.cleanup()
        return self._docs.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        return self._docs.pop(doc_id, None) is not None

    def cleanup(self) -> None:
        now = time.time()
        for key in [k for k, d in self._docs.items() if now - d.created_at > self._ttl]:
            del self._docs[key]
