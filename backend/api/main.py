from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.adapters.extractors import labels as format_labels
from backend.adapters.llm import create_llm_client
from backend.adapters.store import create_store
from backend.api.dependencies import get_settings
from backend.api.middleware import RequestContextMiddleware
from backend.api.routers import documents, ollama, summary
from backend.core.config import Settings
from backend.core.exceptions import SummaryAgentError
from backend.core.logging import setup_logging

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

setup_logging(get_settings())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Tworzy zasoby aplikacji (magazyn, klient LLM) i zamyka je przy wyjściu."""
    settings = get_settings()
    app.state.settings = settings
    app.state.store = create_store(settings)
    app.state.llm_client = create_llm_client(settings)
    try:
        yield
    finally:
        await app.state.llm_client.close()


app = FastAPI(
    title="SummaryAgent",
    description="Wgraj pliki i otrzymaj ich podsumowanie od modelu LLM.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(SummaryAgentError)
async def domain_error_handler(request: Request, exc: SummaryAgentError) -> JSONResponse:
    """Błędy domenowe -> spójne odpowiedzi HTTP bez śladów w 500-kach."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(documents.router)
app.include_router(summary.router)
app.include_router(ollama.router)


@app.get("/api/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
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
