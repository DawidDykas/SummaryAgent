from fastapi import APIRouter

from backend.api.config import get_settings
from backend.api.schemas import OllamaStatus
from backend.api.services.llm import ollama_status

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


@router.get("/status", response_model=OllamaStatus)
async def status() -> OllamaStatus:
    data = await ollama_status(get_settings())
    return OllamaStatus(**data)
