"""Extractor registry - adding a format = one entry in REGISTRY.

To add a new format:
    from backend.adapters.extractors import register
    register(".odt", "ODT", my_extractor)
"""

from __future__ import annotations

from collections.abc import Callable

from backend.core.exceptions import ExtractionError

from . import docx, html, pdf, plain, rtf

Extractor = Callable[[bytes], str]

REGISTRY: dict[str, tuple[str, Extractor]] = {}

# compatibility aliases (refreshed on every register)
FORMATS: dict[str, str] = {}
ACCEPT: str = ""


def register(extension: str, label: str, extractor: Extractor) -> None:
    """Register a file format (extension must start with a dot)."""
    ext = extension.lower()
    if not ext.startswith("."):
        raise ValueError(f"Rozszerzenie musi zaczynać się od kropki: {extension!r}")
    REGISTRY[ext] = (label, extractor)
    FORMATS[ext] = label
    global ACCEPT
    ACCEPT = ",".join(f"*{e}" for e in REGISTRY)


def format_of(file_name: str) -> str | None:
    """Return the human-readable format label, or None when unsupported."""
    dot = file_name.rfind(".")
    if dot == -1:
        return None
    return REGISTRY.get(file_name[dot:].lower(), (None, None))[0]


def extensions() -> list[str]:
    return sorted(REGISTRY)


def labels() -> list[str]:
    """Sorted, unique format labels (e.g. for /api/health)."""
    return sorted({label for label, _ in REGISTRY.values()})


def extract_text(file_name: str, data: bytes) -> tuple[str, str]:
    """Return ``(format, text)``. Raises ExtractionError for unsupported formats."""
    dot = file_name.rfind(".")
    entry = REGISTRY.get(file_name[dot:].lower()) if dot != -1 else None
    if entry is None:
        raise ExtractionError(
            f"Nieobsługiwany format pliku '{file_name}'. Dostępne: {', '.join(labels())}."
        )
    label, extractor = entry
    text = extractor(data)
    if not text:
        raise ExtractionError("Nie udało się wyekstrahować żadnej treści z pliku.")
    return label, text


# --- default formats ---------------------------------------------------------
register(".pdf", "PDF", pdf.extract)
register(".docx", "DOCX", docx.extract)
register(".txt", "TXT", plain.extract)
register(".md", "Markdown", plain.extract)
register(".markdown", "Markdown", plain.extract)
register(".html", "HTML", html.extract)
register(".htm", "HTML", html.extract)
register(".rtf", "RTF", rtf.extract)

__all__ = [
    "ACCEPT",
    "FORMATS",
    "ExtractionError",
    "extract_text",
    "extensions",
    "format_of",
    "labels",
    "register",
]
