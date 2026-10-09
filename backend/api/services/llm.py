import asyncio

import httpx

from backend.api.config import Settings, get_settings
from backend.core.exceptions import LLMError

__all__ = ["LLMError", "chat", "ollama_status"]


def _friendly_external_error(status: int, body: str) -> str:
    if status == 401:
        return "API odrzuciło klucz dostępowy - sprawdź LLM_API_KEY w .env."
    if status == 404:
        return "Nie znaleziono endpointu API - sprawdź LLM_API_URL w .env (powinno wskazywać na /v1)."
    if status == 429:
        return "Przekroczony limit zapytań API - spróbuj ponownie za chwilę."
    snippet = body.strip()[:300]
    return f"API zwróciło błąd HTTP {status}: {snippet}"


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict, headers: dict) -> dict:
    try:
        resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise LLMError("Model nie odpowiedział na czas (timeout). Spróbuj ponownie.") from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"Nie udało się połączyć z modelem: {exc}") from exc
    if resp.status_code >= 400:
        raise LLMError(_friendly_external_error(resp.status_code, resp.text))
    try:
        return resp.json()
    except ValueError as exc:
        raise LLMError("Model zwrócił nieprawidłową odpowiedź (nie-JSON).") from exc


async def _chat_external(settings: Settings, client: httpx.AsyncClient, messages: list[dict], max_tokens: int) -> str:
    url = settings.active_base_url
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key.strip():
        headers["Authorization"] = f"Bearer {settings.llm_api_key.strip()}"
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": settings.summary_temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    data = await _post_json(client, url, payload, headers)
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("API zwróciło odpowiedź w nieoczekiwanym formacie.") from exc
    if not content or not content.strip():
        raise LLMError("Model zwrócił pustą odpowiedź.")
    return content.strip()


async def _chat_ollama(settings: Settings, client: httpx.AsyncClient, messages: list[dict], max_tokens: int) -> str:
    url = f"{settings.active_base_url}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": settings.summary_temperature,
            "num_predict": max_tokens,
        },
    }
    try:
        data = await _post_json(client, url, payload, {"Content-Type": "application/json"})
    except LLMError as exc:
        if "HTTP 404" in str(exc):
            raise LLMError(
                f"Ollama nie znalazła modelu '{settings.ollama_model}'. "
                f"W terminalu uruchom: ollama pull {settings.ollama_model}"
            ) from exc
        raise
    try:
        content = data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise LLMError("Ollama zwróciła odpowiedź w nieoczekiwanym formacie.") from exc
    if not content or not content.strip():
        raise LLMError("Model zwrócił pustą odpowiedź.")
    return content.strip()


async def chat(messages: list[dict], *, max_tokens: int = 1600, settings: Settings | None = None) -> str:
    """Wywołuje aktywny model (zewnętrzne API albo Ollama) z ponowieniami."""
    settings = settings or get_settings()
    timeout = httpx.Timeout(settings.request_timeout, connect=15.0)
    last_error: LLMError | None = None
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(settings.max_retries + 1):
            try:
                if settings.provider == "external":
                    return await _chat_external(settings, client, messages, max_tokens)
                return await _chat_ollama(settings, client, messages, max_tokens)
            except LLMError as exc:
                last_error = exc
                if attempt < settings.max_retries:
                    await asyncio.sleep(1.0 + attempt * 1.5)
    raise last_error or LLMError("Nieznany błąd modelu.")


async def ollama_status(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    base = settings.ollama_base_url.rstrip("/")
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
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
