"""Client for OpenAI-compatible APIs (OpenAI, Groq, OpenRouter, DeepSeek...)."""

from __future__ import annotations

import httpx

from backend.core.config import Settings
from backend.core.exceptions import LLMError
from backend.core.ports.llm import Message


def friendly_error(status: int, body: str) -> str:
    if status == 401:
        return "API odrzuciło klucz dostępowy - sprawdź LLM_API_KEY w .env."
    if status == 404:
        return (
            "Nie znaleziono endpointu API - sprawdź LLM_API_URL w .env "
            "(powinno wskazywać na /v1)."
        )
    if status == 429:
        return "Przekroczony limit zapytań API - spróbuj ponownie za chwilę."
    snippet = body.strip()[:300]
    return f"API zwróciło błąd HTTP {status}: {snippet}"


class OpenAICompatClient:
    """Single /chat/completions call (retries handled by RetryingLLMClient)."""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        timeout = httpx.Timeout(settings.request_timeout, connect=15.0)
        self._client = httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, transport=transport
        )

    async def chat(self, messages: list[Message], *, max_tokens: int = 1600) -> str:
        s = self._settings
        url = s.active_base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if s.llm_api_key.strip():
            headers["Authorization"] = f"Bearer {s.llm_api_key.strip()}"
        payload = {
            "model": s.llm_model,
            "messages": messages,
            "temperature": s.summary_temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        try:
            resp = await self._client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMError("Model nie odpowiedział na czas (timeout). Spróbuj ponownie.") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Nie udało się połączyć z modelem: {exc}") from exc

        if resp.status_code >= 400:
            raise LLMError(friendly_error(resp.status_code, resp.text))
        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMError("Model zwrócił nieprawidłową odpowiedź (nie-JSON).") from exc
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("API zwróciło odpowiedź w nieoczekiwanym formacie.") from exc
        if not content or not content.strip():
            raise LLMError("Model zwrócił pustą odpowiedź.")
        return content.strip()

    async def close(self) -> None:
        await self._client.aclose()
