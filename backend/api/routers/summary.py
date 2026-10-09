import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.api.config import Settings, get_settings
from backend.api.services import llm
from backend.api.services.chunker import split_text
from backend.api.services.prompts import (
    chunk_prompt,
    combine_prompt,
    final_max_tokens,
    final_prompt,
)
from backend.api.services.store import StoredDocument, store

router = APIRouter(prefix="/api", tags=["summary"])

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

LENGTH_PATTERN = "^(short|standard|long|xl)$"

_SENTINEL = object()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _status(step: str, message: str, *, progress: int | None = None, total: int | None = None) -> dict:
    payload: dict[str, Any] = {"step": step, "message": message}
    if progress is not None:
        payload["progress"] = progress
    if total is not None:
        payload["total"] = total
    return payload


async def _analyze_chunks(
    chunks: list[str],
    *,
    name: str,
    settings: Settings,
    queue: asyncio.Queue,
) -> tuple[dict[int, str], list[Exception]]:
    """Analizuje części równolegle (limit = settings.summary_concurrency).

    Zdarzenia statusu trafiają do kolejki, wyniki i błędy są zwracane osobno.
    """
    total = len(chunks)
    concurrency = max(1, min(settings.summary_concurrency, 8))
    semaphore = asyncio.Semaphore(concurrency)
    results: dict[int, str] = {}
    errors: list[Exception] = []
    completed = 0

    async def worker(index: int, chunk: str) -> None:
        nonlocal completed
        async with semaphore:
            await queue.put(("status", _status(
                "thinking", f"Analiza części {index}/{total}...", progress=completed, total=total,
            )))
            try:
                part = await llm.chat(
                    chunk_prompt(name, index, total, chunk),
                    max_tokens=1200,
                    settings=settings,
                )
            except Exception as exc:  # błąd jednej części nie zrywa strumienia
                errors.append(exc)
                return
            results[index] = part
            completed += 1
            await queue.put(("status", _status(
                "thinking",
                f"Ukończono część {index}/{total} ({completed}/{total})",
                progress=completed,
                total=total,
            )))

    async def runner() -> None:
        try:
            await asyncio.gather(*(worker(i, chunk) for i, chunk in enumerate(chunks, start=1)))
        finally:
            await queue.put((_SENTINEL, {}))

    asyncio.create_task(runner())
    return results, errors


async def _event_stream(docs: list[StoredDocument], lang: str, length: str):
    settings = get_settings()
    started = time.perf_counter()

    try:
        yield _sse("status", _status("prepare", f"Łączenie {len(docs)} dokumentów..."))

        sections = [f"== Plik: {d.name} ==\n{d.text}" for d in docs]
        text = "\n\n\n".join(sections).strip()
        name = docs[0].name if len(docs) == 1 else "połączone pliki"
        multi = len(docs) > 1

        chunks = (
            split_text(text, settings.chunk_size, settings.chunk_overlap)
            if len(text) > settings.chunk_size
            else [text]
        )
        total = len(chunks)

        if total > 1:
            yield _sse("status", _status("chunk", f"Duży dokument - dzielenie na {total} części...", total=total))
            queue: asyncio.Queue = asyncio.Queue()
            task = asyncio.create_task(_analyze_chunks(
                chunks, name=name, settings=settings, queue=queue,
            ))
            while True:
                event, data = await queue.get()
                if event is _SENTINEL:
                    break
                yield _sse(event, data)
            results, errors = await task
            if errors:
                raise errors[0]

            yield _sse("status", _status(
                "synthesize", "Zbieranie wniosków w całość...", progress=total, total=total,
            ))
            partials = [results[i] for i in sorted(results)]
            messages = combine_prompt(name, partials, lang=lang, length=length)
        else:
            yield _sse("status", _status("thinking", "Model analizuje dokument...", progress=1, total=1))
            messages = final_prompt(name, text, lang=lang, length=length, multi=multi)

        summary = await llm.chat(messages, max_tokens=final_max_tokens(length), settings=settings)

        yield _sse(
            "done",
            {
                "summary": summary,
                "stats": {
                    "files": len(docs),
                    "chars": len(text),
                    "chunks": total,
                    "duration_s": round(time.perf_counter() - started, 2),
                    "provider": settings.provider,
                    "model": settings.active_model,
                    "lang": lang,
                    "length": length,
                },
                "files": [d.name for d in docs],
            },
        )
    except llm.LLMError as exc:
        yield _sse("error", {"message": str(exc)})
    except Exception as exc:
        yield _sse("error", {"message": f"Nieoczekiwany błąd: {exc}"})


@router.get("/summary/stream")
async def summary_stream(
    doc_ids: str = Query(..., description="Lista id dokumentów po przecinku"),
    lang: str = Query("pl", pattern="^(pl|en)$"),
    length: str = Query("standard", pattern=LENGTH_PATTERN),
):
    ids = [i.strip() for i in doc_ids.split(",") if i.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="Nie wybrano żadnych dokumentów.")
    settings = get_settings()
    if len(ids) > settings.max_files:
        raise HTTPException(status_code=400, detail="Za dużo dokumentów w żądaniu.")

    docs: list[StoredDocument] = []
    missing: list[str] = []
    for doc_id in ids:
        doc = store.get(doc_id)
        if doc is None:
            missing.append(doc_id)
        else:
            docs.append(doc)
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Dokument(y) {', '.join(missing)} wygasł/y - wgraj pliki ponownie.",
        )
    return StreamingResponse(
        _event_stream(docs, lang, length),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
