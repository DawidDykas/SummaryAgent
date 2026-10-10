"""API integration tests: full upload -> SSE summary flow with a fake LLM."""

import json

import pytest

from backend.api import dependencies
from backend.api.main import app
from backend.core.config import Settings
from backend.core.exceptions import LLMError


class FakeLLM:
    def __init__(self, reply: str = "PODSUMOWANIE-LM", error: Exception | None = None):
        self.calls = 0
        self.reply = reply
        self.error = error

    async def chat(self, messages, *, max_tokens: int = 1600) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        return f"{self.reply}-{self.calls}"

    async def close(self) -> None:
        pass


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        event, data = "message", None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if data is not None:
            events.append((event, data))
    return events


def override_llm(fake: FakeLLM):
    app.dependency_overrides[dependencies.get_llm_client] = lambda: fake


def override_settings(settings: Settings):
    app.dependency_overrides[dependencies.get_settings] = lambda: settings


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def upload(client, text: str, name: str = "dok.txt") -> str:
    resp = client.post(
        "/api/documents", files=[("files", (name, text.encode("utf-8"), "text/plain"))]
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["documents"], body["errors"]
    return body["documents"][0]["id"]


def test_summary_stream_with_fake_llm(client):
    fake = FakeLLM(reply="WYNIK")
    override_llm(fake)
    doc_id = upload(client, "Przetarg na dostawę sprzętu.")

    resp = client.get(
        "/api/summary/stream", params={"doc_ids": doc_id, "lang": "pl", "length": "standard"}
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(resp.text)
    kinds = [e for e, _ in events]
    assert kinds == ["status", "status", "done"]

    done = events[-1][1]
    assert done["summary"] == "WYNIK-1"
    assert done["stats"]["chunks"] == 1
    assert done["stats"]["provider"] == "ollama"
    assert fake.calls == 1


def test_summary_stream_multiple_documents(client):
    fake = FakeLLM(reply="SUMA")
    override_llm(fake)
    ids = [upload(client, "treść pierwsza", "a.txt"), upload(client, "treść druga", "b.txt")]

    resp = client.get("/api/summary/stream", params={"doc_ids": ",".join(ids)})

    events = parse_sse(resp.text)
    done = events[-1][1]
    assert events[-1][0] == "done"
    assert done["files"] == ["a.txt", "b.txt"]
    assert done["stats"]["files"] == 2


def test_summary_stream_map_reduce(client):
    fake = FakeLLM(reply="CZĘŚĆ")
    override_llm(fake)
    override_settings(
        Settings(_env_file=None, chunk_size=100, chunk_overlap=0, summary_concurrency=2)
    )
    doc_id = upload(client, "Bardzo długi dokument. " * 60)

    resp = client.get("/api/summary/stream", params={"doc_ids": doc_id, "length": "long"})

    events = parse_sse(resp.text)
    steps = [d["step"] for e, d in events if e == "status"]
    assert events[-1][0] == "done"
    assert "chunk" in steps
    assert "synthesize" in steps
    done = events[-1][1]
    assert done["stats"]["chunks"] > 1
    assert fake.calls == done["stats"]["chunks"] + 1


def test_summary_stream_llm_error_event(client):
    override_llm(FakeLLM(error=LLMError("Model wyłączony")))
    doc_id = upload(client, "treść")

    resp = client.get("/api/summary/stream", params={"doc_ids": doc_id})

    events = parse_sse(resp.text)
    assert events[-1] == ("error", {"message": "Model wyłączony"})


def test_summary_stream_unknown_doc_http_404(client):
    resp = client.get("/api/summary/stream", params={"doc_ids": "nieznany-id"})
    assert resp.status_code == 404


def test_summary_stream_after_delete_returns_404(client):
    doc_id = upload(client, "treść")
    assert client.delete(f"/api/documents/{doc_id}").status_code == 200

    resp = client.get("/api/summary/stream", params={"doc_ids": doc_id})
    assert resp.status_code == 404
