"""Port (interfejs) klienta LLM.

Realizacje: `backend/adapters/llm/openai.py` i `backend/adapters/llm/ollama.py`,
dobierane przez fabrykę `backend.adapters.llm.create_llm_client()`.

Uwaga: ciała metod to świadomie puste `...` - to *kontrakt*, nie brak kodu.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

Message = dict[str, str]


@runtime_checkable
class LLMClient(Protocol):
    """Kontrakt wspólny dla Ollamy i API zgodnych z OpenAI."""

    async def chat(self, messages: list[Message], *, max_tokens: int = 1600) -> str:
        """Zwraca treść odpowiedzi modelu (bez streamingu).

        Implementacje rzucają `backend.core.exceptions.LLMError` przy błędach
        sieci, HTTP lub pustej odpowiedzi.
        """
        ...

    async def close(self) -> None:
        """Zwalnia zasoby (połączenia HTTP) - wywoływane przy shutdowncie aplikacji."""
        ...
