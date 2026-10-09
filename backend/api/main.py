from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.adapters.extractors import labels as format_labels
from backend.api.config import get_settings
from backend.api.routers import documents, ollama, summary
from backend.core.exceptions import SummaryAgentError

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


@app.exception_handler(SummaryAgentError)
async def domain_error_handler(request: Request, exc: SummaryAgentError) -> JSONResponse:
    """Błędy domenowe -> spójne odpowiedzi HTTP bez śladów w 500-kach."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


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
        "supported_formats": format_labels(),
    }


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
