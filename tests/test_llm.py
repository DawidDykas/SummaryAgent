"""Tests for LLM adapters: factory, OpenAI-compat, Ollama, retry."""

import json

import httpx
import pytest

from backend.adapters.llm import create_llm_client
from backend.adapters.llm.ollama import OllamaClient, ollama_status
from backend.adapters.llm.openai import OpenAICompatClient
from backend.adapters.llm.retry import RetryingLLMClient
from backend.core.config import Settings
from backend.core.exceptions import LLMError
from backend.core.ports.llm import LLMClient

MSGS = [{"role": "user", "content": "cześć"}]


def settings(**kw):
    return Settings(_env_file=None, **kw)


def transport(handler):
    return httpx.MockTransport(handler)


# ---------------------------------------------------------------- factory ----


def test_factory_picks_ollama_by_default():
    client = create_llm_client(settings())
    assert isinstance(client, RetryingLLMClient)
    assert isinstance(client._inner, OllamaClient)


def test_factory_picks_openai_when_url_set():
    client = create_llm_client(settings(llm_api_url="https://api.example.com/v1"))
    assert isinstance(client._inner, OpenAICompatClient)


def test_factory_result_satisfies_port():
    assert isinstance(create_llm_client(settings()), LLMClient)


# --------------------------------------------------------------- openai -----


def openai_ok(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    assert body["model"] == "gpt-4o-mini"
    assert body["max_tokens"] == 500
    return httpx.Response(
        200, json={"choices": [{"message": {"content": "  odpowiedź  "}}]}
    )


@pytest.mark.asyncio
async def test_openai_chat_success():
    s = settings(llm_api_url="https://api.example.com/v1")
    client = OpenAICompatClient(s, transport=transport(openai_ok))
    assert await client.chat(MSGS, max_tokens=500) == "odpowiedź"
    await client.close()


@pytest.mark.asyncio
async def test_openai_url_gets_chat_completions_suffix():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = OpenAICompatClient(
        settings(llm_api_url="https://api.example.com/v1/"),
        transport=transport(handler),
    )
    await client.chat(MSGS)
    assert seen == ["https://api.example.com/v1/chat/completions"]
    await client.close()


@pytest.mark.asyncio
async def test_openai_sends_bearer_key():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = OpenAICompatClient(
        settings(llm_api_url="https://api.example.com/v1", llm_api_key="sk-test"),
        transport=transport(handler),
    )
    await client.chat(MSGS)
    assert seen["authorization"] == "Bearer sk-test"
    await client.close()


@pytest.mark.asyncio
async def test_openai_401_friendly_message():
    client = OpenAICompatClient(
        settings(llm_api_url="https://api.example.com/v1"),
        transport=transport(lambda r: httpx.Response(401, text="nope")),
    )
    with pytest.raises(LLMError, match="LLM_API_KEY"):
        await client.chat(MSGS)
    await client.close()


@pytest.mark.asyncio
async def test_openai_429_friendly_message():
    client = OpenAICompatClient(
        settings(llm_api_url="https://api.example.com/v1"),
        transport=transport(lambda r: httpx.Response(429, text="slow down")),
    )
    with pytest.raises(LLMError, match="limit zapytań"):
        await client.chat(MSGS)
    await client.close()


@pytest.mark.asyncio
async def test_openai_empty_content_rejected():
    client = OpenAICompatClient(
        settings(llm_api_url="https://api.example.com/v1"),
        transport=transport(lambda r: httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})),
    )
    with pytest.raises(LLMError, match="pustą odpowiedź"):
        await client.chat(MSGS)
    await client.close()


@pytest.mark.asyncio
async def test_openai_connection_error_wrapped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = OpenAICompatClient(
        settings(llm_api_url="https://api.example.com/v1"),
        transport=transport(handler),
    )
    with pytest.raises(LLMError, match="Nie udało się połączyć"):
        await client.chat(MSGS)
    await client.close()


# --------------------------------------------------------------- ollama ------


@pytest.mark.asyncio
async def test_ollama_chat_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        body = json.loads(request.content)
        assert body["model"] == "llama3.2"
        assert body["options"]["num_predict"] == 700
        return httpx.Response(200, json={"message": {"content": "streszczenie"}})

    client = OllamaClient(settings(), transport=transport(handler))
    assert await client.chat(MSGS, max_tokens=700) == "streszczenie"
    await client.close()


@pytest.mark.asyncio
async def test_ollama_404_suggests_pull():
    client = OllamaClient(
        settings(),
        transport=transport(lambda r: httpx.Response(404, text="model not found")),
    )
    with pytest.raises(LLMError, match="ollama pull llama3.2"):
        await client.chat(MSGS)
    await client.close()


@pytest.mark.asyncio
async def test_ollama_status_model_ready():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "llama3.2:latest"}]})

    status = await ollama_status(settings(), transport=transport(handler))
    assert status["reachable"] is True
    assert status["model_ready"] is True
    assert status["detail"] == ""


@pytest.mark.asyncio
async def test_ollama_status_model_missing():
    status = await ollama_status(
        settings(),
        transport=transport(lambda r: httpx.Response(200, json={"models": []})),
    )
    assert status["model_ready"] is False
    assert "ollama pull" in status["detail"]


@pytest.mark.asyncio
async def test_ollama_status_unreachable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    status = await ollama_status(settings(), transport=transport(handler))
    assert status["reachable"] is False
    assert "Brak połączenia" in status["detail"]


# ----------------------------------------------------------------- retry -----


class FlakyClient:
    def __init__(self, fails: int, delay: float = 0.0):
        self.fails = fails
        self.calls = 0
        self.delay = delay

    async def chat(self, messages, *, max_tokens: int = 1600) -> str:
        self.calls += 1
        import asyncio

        if self.delay:
            await asyncio.sleep(self.delay)
        if self.calls <= self.fails:
            raise LLMError("chwilowy błąd")
        return "ok"

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_retry_recovers_from_transient_error():
    inner = FlakyClient(fails=2)
    client = RetryingLLMClient(inner, max_retries=2, base_delay=0.0, backoff=0.0)
    assert await client.chat(MSGS) == "ok"
    assert inner.calls == 3


@pytest.mark.asyncio
async def test_retry_gives_up_after_max_attempts():
    inner = FlakyClient(fails=99)
    client = RetryingLLMClient(inner, max_retries=2, base_delay=0.0, backoff=0.0)
    with pytest.raises(LLMError, match="chwilowy błąd"):
        await client.chat(MSGS)
    assert inner.calls == 3  # 1 + 2 ponowienia
