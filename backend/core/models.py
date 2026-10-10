"""Domain models (core-layer entities, independent of FastAPI)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


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

    @classmethod
    def create(cls, name: str, fmt: str, text: str, chunks: int) -> StoredDocument:
        return cls(
            id=uuid.uuid4().hex[:12],
            name=name,
            fmt=fmt,
            text=text,
            chars=len(text),
            words=len(text.split()),
            chunks=chunks,
        )
