"""Document upload handling: validation, extraction, chunking, store."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from backend.core.chunking import split_text
from backend.core.config import Settings
from backend.core.exceptions import BadRequestError, ExtractionError
from backend.core.models import StoredDocument
from backend.core.ports.extractor import TextExtractor
from backend.core.ports.store import DocumentStore


@dataclass(frozen=True)
class FileResult:
    """Result of processing a single file (document XOR error)."""

    name: str
    document: StoredDocument | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.document is not None


@dataclass
class DocumentService:
    store: DocumentStore
    settings: Settings
    extract: TextExtractor

    async def upload(self, items: Sequence[tuple[str, bytes]]) -> list[FileResult]:
        """Process files (name, bytes) - each independently (one failure does not block the rest)."""
        if len(items) > self.settings.max_files:
            raise BadRequestError(
                f"Za dużo plików naraz - maksymalnie {self.settings.max_files}."
            )
        results: list[FileResult] = []
        for name, data in items:
            try:
                # extraction is CPU-bound -> run in a thread to keep the event loop free
                doc = await asyncio.to_thread(self._register, name, data)
                results.append(FileResult(name=name, document=doc))
            except BadRequestError as exc:
                results.append(FileResult(name=name, error=exc.message))
            except ExtractionError as exc:
                results.append(FileResult(name=name, error=exc.message))
            except Exception:  # unexpected read errors must not leak details
                results.append(FileResult(name=name, error="Nie udało się odczytać pliku."))
        return results

    def _register(self, name: str, data: bytes) -> StoredDocument:
        limit = self.settings.max_file_size_mb * 1024 * 1024
        if len(data) > limit:
            raise BadRequestError(f"Plik przekracza limit {self.settings.max_file_size_mb} MB.")
        if not data:
            raise BadRequestError("Plik jest pusty.")

        fmt, text = self.extract(name, data)
        chunks = split_text(text, self.settings.chunk_size, self.settings.chunk_overlap)
        return self.store.put(name, fmt, text, chunks=len(chunks))
