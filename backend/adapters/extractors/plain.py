"""Extract text from plain-text files (TXT, MD) - no conversion needed."""

from __future__ import annotations

from backend.core.exceptions import ExtractionError

from .base import clean, decode


def extract(data: bytes) -> str:
    text = clean(decode(data))
    if not text:
        raise ExtractionError("Plik jest pusty.")
    return text
