from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.config import get_settings
from backend.api.routers import documents, ollama, summary
from backend.api.services.extractors import FORMATS

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

app = FastAPI(
    title="SummaryAgent",
    description="Wgraj pliki i otrzymaj ich podsumowanie od modelu LLM.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(summary.router)
app.include_router(ollama.router)


@app.get("/api/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "provider": settings.provider,
        "model": settings.active_model,
        "label": settings.active_label,
        "base_url": settings.active_base_url,
        "supported_formats": sorted(set(FORMATS.values())),
    }


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
