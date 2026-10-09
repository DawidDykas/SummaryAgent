from fastapi import APIRouter, Depends

from backend.adapters.llm import ollama_status
from backend.api.dependencies import get_settings
from backend.api.schemas import OllamaStatus
from backend.core.config import Settings

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


@router.get("/status", response_model=OllamaStatus)
async def status(settings: Settings = Depends(get_settings)) -> OllamaStatus:
    data = await ollama_status(settings)
    return OllamaStatus(**data)
