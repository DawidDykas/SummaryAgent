"""Shared extractor helpers: byte decoding and text cleanup."""

from __future__ import annotations

ENCODINGS = ("utf-8-sig", "utf-8", "cp1250", "latin-1")


def decode(data: bytes) -> str:
    for enc in ENCODINGS:
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def clean(text: str) -> str:
    import re

    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
