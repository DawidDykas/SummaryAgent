import time
import uuid
from dataclasses import dataclass, field

from backend.api.config import get_settings


@dataclass
class StoredDocument:
    id: str
    name: str
    fmt: str
    text: str
    chars: int
    words: int
    chunks: int
    created_at: float = field(default_factory=time.time)


class DocumentStore:
    """Prosty magazyn dokumentów w pamięci procesu (z TTL)."""

    def __init__(self) -> None:
        self._docs: dict[str, StoredDocument] = {}

    def put(self, name: str, fmt: str, text: str, chunks: int) -> StoredDocument:
        self.cleanup()
        doc = StoredDocument(
            id=uuid.uuid4().hex[:12],
            name=name,
            fmt=fmt,
            text=text,
            chars=len(text),
            words=len(text.split()),
            chunks=chunks,
        )
        self._docs[doc.id] = doc
        return doc

    def get(self, doc_id: str) -> StoredDocument | None:
        self.cleanup()
        return self._docs.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        return self._docs.pop(doc_id, None) is not None

    def cleanup(self) -> None:
        ttl = get_settings().doc_ttl_seconds
        now = time.time()
        for key in [k for k, d in self._docs.items() if now - d.created_at > ttl]:
            del self._docs[key]


store = DocumentStore()
