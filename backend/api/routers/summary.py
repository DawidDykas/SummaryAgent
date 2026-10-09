import json
import time

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.api.config import get_settings
from backend.api.services import llm
from backend.api.services.chunker import split_text
from backend.api.services.prompts import chunk_prompt, combine_prompt, final_prompt
from backend.api.services.store import store

router = APIRouter(prefix="/api", tags=["summary"])

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _event_stream(docs: list, lang: str, length: str):
    settings = get_settings()
    started = time.perf_counter()

    try:
        yield _sse(
            "status",
            {"step": "prepare", "message": f"Łączenie {len(docs)} dokumentów...", "progress": 0},
        )
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
            yield _sse(
                "status",
                {
                    "step": "chunk",
                    "message": f"Duży dokument - dzielenie na {total} części...",
                    "progress": 0,
                    "total": total,
                },
            )

        partials: list[str] = []
        if total > 1:
            for i, chunk in enumerate(chunks, start=1):
                yield _sse(
                    "status",
                    {
                        "step": "thinking",
                        "message": f"Analiza części {i}/{total}...",
                        "progress": i,
                        "total": total,
                    },
                )
                part = await llm.chat(
                    chunk_prompt(name, i, total, chunk),
                    max_tokens=1200,
                    settings=settings,
                )
                partials.append(part)

            yield _sse(
                "status",
                {"step": "synthesize", "message": "Zbieranie wniosków w całość...", "progress": total, "total": total},
            )
            messages = combine_prompt(name, partials, lang=lang, length=length)
        else:
            yield _sse("status", {"step": "thinking", "message": "Model analizuje dokument...", "progress": 1, "total": 1})
            messages = final_prompt(name, text, lang=lang, length=length, multi=multi)

        summary = await llm.chat(messages, max_tokens=2000, settings=settings)

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
    length: str = Query("standard", pattern="^(short|standard|long)$"),
):
    ids = [i.strip() for i in doc_ids.split(",") if i.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="Nie wybrano żadnych dokumentów.")
    settings = get_settings()
    if len(ids) > settings.max_files:
        raise HTTPException(status_code=400, detail="Za dużo dokumentów w żądaniu.")
    docs = []
    missing = []
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
    return StreamingResponse(_event_stream(docs, lang, length), media_type="text/event-stream", headers=SSE_HEADERS)
