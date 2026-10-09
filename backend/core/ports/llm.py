"""Port (interfejs) klienta LLM - implementacje żyją w backend.adapters.llm."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

Message = dict[str, str]


@runtime_checkable
class LLMClient(Protocol):
    """Kontrakt wspólny dla Ollamy i API zgodnych z OpenAI."""

    async def chat(self, messages: list[Message], *, max_tokens: int = 1600) -> str:
        """Zwraca treść odpowiedzi modelu. Błędy = backend.core.exceptions.LLMError."""
        ...

    async def close(self) -> None:
        ...
