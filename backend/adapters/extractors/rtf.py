"""Extract text from RTF."""

from __future__ import annotations

from striprtf.striprtf import rtf_to_text

from backend.core.exceptions import ExtractionError

from .base import clean


def extract(data: bytes) -> str:
    raw = data.decode("latin-1", errors="replace")
    try:
        text = rtf_to_text(raw, errors="ignore")
    except Exception as exc:
        raise ExtractionError(f"Nie udało się odczytać pliku RTF ({exc}).") from exc
    text = clean(text)
    if not text:
        raise ExtractionError("Plik RTF jest pusty.")
    return text
