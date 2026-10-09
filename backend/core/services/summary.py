"""Orchestration podsumowania: map-reduce dla dużych dokumentów + strumień zdarzeń.

Zwraca zdarzenia ((nazwa_eventu, payload)) - formatowanie SSE to zadanie warstwy API.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

from backend.core.chunking import split_text
from backend.core.config import Settings
from backend.core.exceptions import BadRequestError, DocumentNotFoundError, LLMError
from backend.core.models import StoredDocument
from backend.core.ports.llm import LLMClient
from backend.core.ports.store import DocumentStore
from backend.core.prompts import (
    chunk_prompt,
    combine_prompt,
    final_max_tokens,
    final_prompt,
)

Event = tuple[str, dict[str, Any]]

_SENTINEL = object()

_MESSAGES: dict[str, dict[str, str]] = {
    "pl": {
        "prepare": "Łączenie {n} dokumentów...",
        "chunk": "Duży dokument - dzielenie na {total} części...",
        "synthesize": "Zbieranie wniosków w całość...",
        "thinking": "Model analizuje dokument...",
        "analyze_start": "Analiza części {index}/{total}...",
        "analyze_done": "Ukończono część {index}/{total} ({completed}/{total})",
        "unexpected": "Nieoczekiwany błąd: {error}",
    },
    "en": {
        "prepare": "Combining {n} documents...",
        "chunk": "Large document - splitting into {total} parts...",
        "synthesize": "Putting the conclusions together...",
        "thinking": "The model is analyzing the document...",
        "analyze_start": "Analyzing part {index}/{total}...",
        "analyze_done": "Completed part {index}/{total} ({completed}/{total})",
        "unexpected": "Unexpected error: {error}",
    },
}


def _msg(lang: str, key: str, **vars: object) -> str:
    """Komunikat statusu w wybranym języku (fallback: pl)."""
    table = _MESSAGES.get(lang) or _MESSAGES["pl"]
    template = table.get(key) or _MESSAGES["pl"][key]
    return template.format(**vars)


def _status(
    step: str, message: str, *, progress: int | None = None, total: int | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"step": step, "message": message}
    if progress is not None:
        payload["progress"] = progress
    if total is not None:
        payload["total"] = total
    return payload


@dataclass
class SummaryService:
    store: DocumentStore
    client: LLMClient
    settings: Settings

    def resolve(self, doc_ids: Sequence[str]) -> list[StoredDocument]:
        """Pobiera dokumenty z magazynu - błędy jako wyjątki (przed startem strumienia)."""
        ids = [i.strip() for i in doc_ids if i.strip()]
        if not ids:
            raise BadRequestError("Nie wybrano żadnych dokumentów.")
        if len(ids) > self.settings.max_files:
            raise BadRequestError("Za dużo dokumentów w żądaniu.")

        docs: list[StoredDocument] = []
        missing: list[str] = []
        for doc_id in ids:
            doc = self.store.get(doc_id)
            if doc is None:
                missing.append(doc_id)
            else:
                docs.append(doc)
        if missing:
            raise DocumentNotFoundError(missing)
        return docs

    async def events(
        self, docs: Sequence[StoredDocument], lang: str, length: str
    ) -> AsyncIterator[Event]:
        """Generuje zdarzenia: status* -> done | error."""
        started = time.perf_counter()
        try:
            yield "status", _status("prepare", _msg(lang, "prepare", n=len(docs)))

            sections = [f"== Plik: {d.name} ==\n{d.text}" for d in docs]
            text = "\n\n\n".join(sections).strip()
            name = docs[0].name if len(docs) == 1 else "połączone pliki"
            multi = len(docs) > 1

            chunks = (
                split_text(text, self.settings.chunk_size, self.settings.chunk_overlap)
                if len(text) > self.settings.chunk_size
                else [text]
            )
            total = len(chunks)

            if total > 1:
                yield "status", _status(
                    "chunk", _msg(lang, "chunk", total=total), total=total
                )
                queue: asyncio.Queue = asyncio.Queue()
                task = asyncio.create_task(self._analyze_chunks(chunks, name, queue, lang))
                while True:  # przekaż statusy części do momentu zakończenia
                    item = await queue.get()
                    if item is _SENTINEL:
                        break
                    yield item
                partials, errors = await task
                if errors:
                    raise errors[0]

                yield "status", _status(
                    "synthesize",
                    _msg(lang, "synthesize"),
                    progress=total,
                    total=total,
                )
                messages = combine_prompt(name, partials, lang=lang, length=length)
            else:
                yield "status", _status(
                    "thinking", _msg(lang, "thinking"), progress=1, total=1
                )
                messages = final_prompt(name, text, lang=lang, length=length, multi=multi)

            summary = await self.client.chat(messages, max_tokens=final_max_tokens(length))

            yield "done", {
                "summary": summary,
                "stats": {
                    "files": len(docs),
                    "chars": len(text),
                    "chunks": total,
                    "duration_s": round(time.perf_counter() - started, 2),
                    "provider": self.settings.provider,
                    "model": self.settings.active_model,
                    "lang": lang,
                    "length": length,
                },
                "files": [d.name for d in docs],
            }
        except LLMError as exc:
            yield "error", {"message": str(exc)}
        except Exception as exc:
            yield "error", {"message": _msg(lang, "unexpected", error=exc)}

    async def _analyze_chunks(
        self,
        chunks: list[str],
        name: str,
        queue: asyncio.Queue,
        lang: str,
    ) -> tuple[list[str], list[Exception]]:
        """Analizuje części równolegle (limit = settings.summary_concurrency).

        Statusy trafiają do kolejki, na końcu wrzucany jest _SENTINEL.
        Zwraca (wyniki w kolejności części, błędy).
        """
        total = len(chunks)
        concurrency = max(1, min(self.settings.summary_concurrency, 8))
        semaphore = asyncio.Semaphore(concurrency)
        results: dict[int, str] = {}
        errors: list[Exception] = []
        completed = 0

        async def worker(index: int, chunk: str) -> None:
            nonlocal completed
            async with semaphore:
                await queue.put(
                    (
                        "status",
                        _status(
                            "thinking",
                            _msg(lang, "analyze_start", index=index, total=total),
                            progress=completed,
                            total=total,
                        ),
                    )
                )
                try:
                    part = await self.client.chat(
                        chunk_prompt(name, index, total, chunk),
                        max_tokens=1200,
                    )
                except Exception as exc:  # błąd jednej części nie zrywa strumienia
                    errors.append(exc)
                    return
                results[index] = part
                completed += 1
                await queue.put(
                    (
                        "status",
                        _status(
                            "thinking",
                            _msg(
                                lang,
                                "analyze_done",
                                index=index,
                                total=total,
                                completed=completed,
                            ),
                            progress=completed,
                            total=total,
                        ),
                    )
                )

        try:
            await asyncio.gather(*(worker(i, c) for i, c in enumerate(chunks, start=1)))
        finally:
            await queue.put(_SENTINEL)

        partials = [results[i] for i in sorted(results)]
        return partials, errors
