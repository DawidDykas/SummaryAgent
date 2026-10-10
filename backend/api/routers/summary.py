import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_summary_service
from backend.core.services.summary import Event, SummaryService

router = APIRouter(prefix="/api", tags=["summary"])

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

LENGTH_PATTERN = "^(short|standard|long|xl)$"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _event_stream(events: AsyncIterator[Event]) -> AsyncIterator[str]:
    """Format domain events into an SSE stream."""
    async for event, data in events:
        yield _sse(event, data)


@router.get("/summary/stream")
async def summary_stream(
    doc_ids: str = Query(..., description="Comma-separated list of document ids"),
    lang: str = Query("pl", pattern="^(pl|en)$", description="summary language"),
    length: str = Query("standard", pattern=LENGTH_PATTERN),
    ui_lang: str | None = Query(None, pattern="^(pl|en)$", description="UI message language"),
    service: SummaryService = Depends(get_summary_service),
):
    # resolve raises BEFORE the response starts (correct HTTP status code)
    docs = service.resolve(doc_ids.split(","))
    return StreamingResponse(
        _event_stream(service.events(docs, lang, length, msg_lang=ui_lang)),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
