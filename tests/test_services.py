"""Tests for domain services (without HTTP)."""

import pytest

from backend.adapters.store import InMemoryDocumentStore
from backend.core.config import Settings
from backend.core.exceptions import BadRequestError, DocumentNotFoundError, ExtractionError
from backend.core.services.documents import DocumentService
from backend.core.services.summary import SummaryService


class FakeLLM:
    def __init__(self, reply: str = "PODSUMOWANIE", error: Exception | None = None):
        self.calls = 0
        self.reply = reply
        self.error = error

    async def chat(self, messages, *, max_tokens: int = 1600) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        return self.reply

    async def close(self) -> None:
        pass


def make_settings(**kw) -> Settings:
    defaults: dict = {"_env_file": None, "chunk_overlap": 0}
    defaults.update(kw)
    return Settings(**defaults)


def make_document_service(settings: Settings | None = None, extract=None) -> DocumentService:
    from backend.adapters.extractors import extract_text

    return DocumentService(
        store=InMemoryDocumentStore(),
        settings=settings or make_settings(),
        extract=extract or extract_text,
    )


def make_summary_service(
    client: FakeLLM | None = None,
    settings: Settings | None = None,
    texts: tuple[str, ...] = ("Zawartość dokumentu.",),
) -> tuple[SummaryService, list]:
    """Service with documents pre-registered in the store (returns those that exist)."""
    store = InMemoryDocumentStore()
    docs = [store.put(f"dok{i}.txt", "TXT", text, chunks=1) for i, text in enumerate(texts)]
    service = SummaryService(
        store=store,
        client=client or FakeLLM(),
        settings=settings or make_settings(),
    )
    return service, docs


# ---------------------------------------------------------- DocumentService ---


@pytest.mark.asyncio
async def test_upload_success():
    service = make_document_service()
    results = await service.upload([("a.txt", b"Ala ma kota. ")])

    assert len(results) == 1
    result = results[0]
    assert result.ok and result.document is not None
    assert result.document.fmt == "TXT"
    assert result.document.chunks == 1


@pytest.mark.asyncio
async def test_upload_too_many_files_rejected():
    service = make_document_service(make_settings(max_files=1))
    items = [(f"f{i}.txt", b"tekst") for i in range(3)]
    with pytest.raises(BadRequestError, match="Za dużo plików"):
        await service.upload(items)


@pytest.mark.asyncio
async def test_upload_isolates_file_errors():
    service = make_document_service()
    results = await service.upload(
        [
            ("ok.txt", "treść".encode()),
            ("zly.exe", b"MZ"),
            ("pusty.txt", b""),
            ("zly.pdf", b"nie pdf"),
        ]
    )

    assert [r.ok for r in results] == [True, False, False, False]
    assert "Nieobsługiwany format" in results[1].error
    assert results[2].error == "Plik jest pusty."
    assert "PDF" in results[3].error


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file():
    service = make_document_service(make_settings(max_file_size_mb=1))
    results = await service.upload([("duzy.txt", b"x" * (1024 * 1024 + 1))])
    assert results[0].error == "Plik przekracza limit 1 MB."


@pytest.mark.asyncio
async def test_upload_unexpected_error_is_masked():
    def broken_extractor(name: str, data: bytes) -> tuple[str, str]:
        raise RuntimeError("wewnętrzny szczegół")

    service = make_document_service(extract=broken_extractor)
    results = await service.upload([("a.txt", b"tekst")])
    assert results[0].error == "Nie udało się odczytać pliku."
    assert "wewnętrzny szczegół" not in results[0].error


@pytest.mark.asyncio
async def test_upload_puts_document_in_store():
    service = make_document_service()
    results = await service.upload([("a.txt", b"tekst")])
    doc_id = results[0].document.id
    assert service.store.get(doc_id) is results[0].document


# ----------------------------------------------------------- SummaryService ---


def test_resolve_returns_docs():
    service, docs = make_summary_service()
    assert service.resolve([docs[0].id]) == docs


def test_resolve_rejects_empty_ids():
    service, _ = make_summary_service()
    with pytest.raises(BadRequestError, match="Nie wybrano"):
        service.resolve(["  ", ""])


def test_resolve_rejects_too_many_ids():
    service, _ = make_summary_service()
    service.settings = make_settings(max_files=1)
    with pytest.raises(BadRequestError, match="Za dużo"):
        service.resolve(["a", "b"])


def test_resolve_missing_docs():
    service, _ = make_summary_service()
    with pytest.raises(DocumentNotFoundError) as exc:
        service.resolve(["brak1", "brak2"])
    assert exc.value.doc_ids == ["brak1", "brak2"]


@pytest.mark.asyncio
async def test_events_single_document_flow():
    client = FakeLLM(reply="GOTOWE")
    service, docs = make_summary_service(client=client)

    events = [event async for event in service.events(docs, "pl", "standard")]

    assert [e for e, _ in events] == ["status", "status", "done"]
    assert events[0][1]["step"] == "prepare"
    assert events[1][1]["step"] == "thinking"
    done = events[-1][1]
    assert done["summary"] == "GOTOWE"
    assert done["stats"]["files"] == 1
    assert done["stats"]["chunks"] == 1
    assert done["stats"]["lang"] == "pl"
    assert client.calls == 1


@pytest.mark.asyncio
async def test_events_map_reduce_for_long_document():
    long_text = ("Zdanie opisujące sprawę. " * 40).strip()  # ~1000 znaków
    settings = make_settings(chunk_size=100, summary_concurrency=2)
    client = FakeLLM(reply="frag")
    service, docs = make_summary_service(
        client=client, settings=settings, texts=(long_text,)
    )

    events = [event async for event in service.events(docs, "pl", "long")]
    steps = [d["step"] for e, d in events if e == "status"]

    assert "chunk" in steps
    assert "synthesize" in steps
    assert events[-1][0] == "done"
    done = events[-1][1]
    assert done["stats"]["chunks"] > 1
    assert client.calls == done["stats"]["chunks"] + 1  # części + scalenie


@pytest.mark.asyncio
async def test_events_llm_error_becomes_error_event():
    from backend.core.exceptions import LLMError

    client = FakeLLM(error=LLMError("Model niedostępny"))
    service, docs = make_summary_service(client=client)

    events = [event async for event in service.events(docs, "pl", "short")]

    assert events[-1][0] == "error"
    assert events[-1][1]["message"] == "Model niedostępny"


@pytest.mark.asyncio
async def test_events_unexpected_error_is_wrapped():
    client = FakeLLM(error=RuntimeError("zk symptom"))
    service, docs = make_summary_service(client=client)

    events = [event async for event in service.events(docs, "pl", "short")]

    assert events[-1][0] == "error"
    assert events[-1][1]["message"].startswith("Nieoczekiwany błąd:")


@pytest.mark.asyncio
async def test_events_failed_chunk_yields_error():
    from backend.core.exceptions import LLMError

    long_text = ("Zdanie. " * 200).strip()
    settings = make_settings(chunk_size=100, summary_concurrency=2)
    client = FakeLLM(error=LLMError("część padła"))
    service, docs = make_summary_service(
        client=client, settings=settings, texts=(long_text,)
    )

    events = [event async for event in service.events(docs, "pl", "short")]
    assert events[-1][0] == "error"
    assert events[-1][1]["message"] == "część padła"


@pytest.mark.asyncio
async def test_events_multiple_documents_are_combined():
    client = FakeLLM(reply="WYNIK")
    service, docs = make_summary_service(client=client, texts=("treść A", "treść B"))

    events = [event async for event in service.events(docs, "en", "xl")]
    done = events[-1][1]

    assert done["summary"] == "WYNIK"
    assert done["files"] == ["dok0.txt", "dok1.txt"]
    assert done["stats"]["files"] == 2
    assert done["stats"]["length"] == "xl"


async def test_status_messages_follow_lang():
    """Stream messages must be in the language chosen in the request."""
    client = FakeLLM(reply="WYNIK")
    service_pl, docs = make_summary_service(client=client, texts=("treść A",))
    msgs_pl = [
        d["message"] for e, d in [x async for x in service_pl.events(docs, "pl", "standard")] if e == "status"
    ]
    assert any("Łączenie" in m for m in msgs_pl)

    client_en = FakeLLM(reply="WYNIK")
    service_en, docs_en = make_summary_service(client=client_en, texts=("treść A",))
    msgs_en = [
        d["message"] for e, d in [x async for x in service_en.events(docs_en, "en", "standard")] if e == "status"
    ]
    assert any("Combining" in m for m in msgs_en)
    assert not any("Łączenie" in m for m in msgs_en)


def test_extraction_error_is_raised_by_register():
    service = make_document_service()
    with pytest.raises(ExtractionError):
        service._register("zly.pdf", b"nie jest pdf")
