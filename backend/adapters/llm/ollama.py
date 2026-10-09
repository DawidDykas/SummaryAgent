"""Klient lokalnej Ollamy + diagnostyka statusu (endpoint /api/ollama/status)."""

from __future__ import annotations

import httpx

from backend.core.config import Settings
from backend.core.exceptions import LLMError
from backend.core.ports.llm import Message


class OllamaClient:
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
        url = f"{s.active_base_url}/api/chat"
        payload = {
            "model": s.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": s.summary_temperature, "num_predict": max_tokens},
        }
        try:
            resp = await self._client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMError("Model nie odpowiedział na czas (timeout). Spróbuj ponownie.") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Nie udało się połączyć z modelem: {exc}") from exc
        if resp.status_code >= 400:
            if resp.status_code == 404:
                raise LLMError(
                    f"Ollama nie znalazła modelu '{s.ollama_model}'. "
                    f"W terminalu uruchom: ollama pull {s.ollama_model}"
                )
            raise LLMError(f"Ollama zwróciła błąd HTTP {resp.status_code}: {resp.text[:300]}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMError("Ollama zwróciła nieprawidłową odpowiedź (nie-JSON).") from exc
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError("Ollama zwróciła odpowiedź w nieoczekiwanym formacie.") from exc
        if not content or not content.strip():
            raise LLMError("Model zwrócił pustą odpowiedź.")
        return content.strip()

    async def close(self) -> None:
        await self._client.aclose()


async def ollama_status(
    settings: Settings,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict:
    """Czy Ollama odpowiada i czy model jest pobrany (dla /api/ollama/status)."""
    base = settings.ollama_base_url.rstrip("/")
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
        try:
            resp = await client.get(f"{base}/api/tags")
            resp.raise_for_status()
            names = [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception as exc:
            return {
                "reachable": False,
                "base_url": base,
                "model": settings.ollama_model,
                "model_ready": None,
                "models": [],
                "detail": f"Brak połączenia z Ollamą: {exc}",
            }
    model = settings.ollama_model
    ready = any(n == model or n.split(":")[0] == model for n in names)
    return {
        "reachable": True,
        "base_url": base,
        "model": model,
        "model_ready": ready,
        "models": names,
        "detail": "" if ready else f"Model '{model}' nie jest jeszcze pobrany: ollama pull {model}",
    }
