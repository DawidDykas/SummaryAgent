"""Port (interfejs) ekstraktora tekstu z pliku.

Realizacja: rejestr w `backend/adapters/extractors/` (wywoływany przez
DocumentService jako zwykły callable).

Uwaga: ciało metody to świadomie puste `...` - to *kontrakt*, nie brak kodu.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TextExtractor(Protocol):
    """Callable: (nazwa pliku, bajty) -> (format, tekst)."""

    def __call__(self, file_name: str, data: bytes) -> tuple[str, str]:
        """Zwraca (format, tekst).

        Implementacje rzucają `backend.core.exceptions.ExtractionError`
        dla nieobsługiwanych formatów i błędów odczytu.
        """
        ...
