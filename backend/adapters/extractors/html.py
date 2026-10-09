"""Ekstrakcja tekstu z HTML (bez script/style)."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import clean, decode


def extract(data: bytes) -> str:
    soup = BeautifulSoup(decode(data), "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return clean(text)
