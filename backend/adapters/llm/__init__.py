"""LLM client factory - single place to pick the provider (OpenAI-compat / Ollama)."""

from __future__ import annotations

import httpx

from backend.core.config import Settings
from backend.core.ports.llm import LLMClient

from .ollama import OllamaClient, ollama_status
from .openai import OpenAICompatClient
from .retry import RetryingLLMClient

__all__ = ["create_llm_client", "ollama_status"]


def create_llm_client(
    settings: Settings,
    transport: httpx.AsyncBaseTransport | None = None,
) -> LLMClient:
    """Return a client with retry policy for the active provider."""
    if settings.provider == "external":
        inner: LLMClient = OpenAICompatClient(settings, transport=transport)
    else:
        inner = OllamaClient(settings, transport=transport)
    return RetryingLLMClient(inner, max_retries=settings.max_retries)
