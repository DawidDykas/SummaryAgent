"""Ponowienia (retry) dowolnego klienta LLM - wspólna polityka dla wszystkich providerów."""

from __future__ import annotations

import asyncio

from backend.core.exceptions import LLMError
from backend.core.ports.llm import LLMClient, Message


class RetryingLLMClient:
    """Dekorator: powtarza wywołanie przy LLMError z liniowym backoffem."""

    def __init__(
        self,
        inner: LLMClient,
        *,
        max_retries: int = 2,
        base_delay: float = 1.0,
        backoff: float = 1.5,
    ) -> None:
        self._inner = inner
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._backoff = backoff

    async def chat(self, messages: list[Message], *, max_tokens: int = 1600) -> str:
        last_error: LLMError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._inner.chat(messages, max_tokens=max_tokens)
            except LLMError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(self._base_delay + attempt * self._backoff)
        raise last_error or LLMError("Nieznany błąd modelu.")

    async def close(self) -> None:
        await self._inner.close()
