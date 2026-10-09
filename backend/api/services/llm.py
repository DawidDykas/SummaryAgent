"""Fasada LLM dla warstwy API (kompatybilność) - logika żyje w backend.adapters.llm."""

from __future__ import annotations

from backend.adapters.llm import create_llm_client
from backend.adapters.llm import ollama_status as _ollama_status
from backend.api.config import Settings, get_settings
from backend.core.exceptions import LLMError
from backend.core.ports.llm import Message

__all__ = ["LLMError", "chat", "ollama_status"]


async def chat(
    messages: list[Message],
    *,
    max_tokens: int = 1600,
    settings: Settings | None = None,
) -> str:
    """Wywołuje aktywny model (zewnętrzne API albo Ollama) z ponowieniami."""
    settings = settings or get_settings()
    client = create_llm_client(settings)
    try:
        return await client.chat(messages, max_tokens=max_tokens)
    finally:
        await client.close()


async def ollama_status(settings: Settings | None = None) -> dict:
    return await _ollama_status(settings or get_settings())
