"""Extract text from PDF (requires a text layer - not a scan)."""

from __future__ import annotations

import io

from pypdf import PdfReader

from backend.core.exceptions import ExtractionError

from .base import clean


def extract(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"Nie udało się odczytać pliku PDF ({exc}).") from exc
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    text = clean("\n\n".join(pages))
    if not text:
        raise ExtractionError(
            "PDF nie zawiera warstwy tekstowej (prawdopodobnie skan) - nie da się go streszczyć."
        )
    return text
