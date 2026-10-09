"""Port ekstraktora tekstu - implementacje w backend.adapters.extractors."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TextExtractor(Protocol):
    def __call__(self, file_name: str, data: bytes) -> tuple[str, str]:
        """Zwraca (format, tekst). Błędy = backend.core.exceptions.ExtractionError."""
        ...
