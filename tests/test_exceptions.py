"""Testy hierarchii wyjątków i exception handlerów API."""

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.exceptions import (
    BadRequestError,
    DocumentNotFoundError,
    ExtractionError,
    LLMError,
    SummaryAgentError,
)

client = TestClient(app)


def test_exception_hierarchy():
    assert issubclass(BadRequestError, SummaryAgentError)
    assert issubclass(DocumentNotFoundError, SummaryAgentError)
    assert issubclass(ExtractionError, SummaryAgentError)
    assert issubclass(LLMError, SummaryAgentError)
    assert BadRequestError("x").status_code == 400
    assert DocumentNotFoundError("x").status_code == 404
    assert ExtractionError("x").status_code == 422
    assert LLMError("x").status_code == 502


def test_document_not_found_custom_message():
    err = DocumentNotFoundError("abc", message="Dokument nie istnieje.")
    assert err.message == "Dokument nie istnieje."
    assert err.doc_ids == ["abc"]


def test_delete_missing_document_returns_404():
    resp = client.delete("/api/documents/nie-ma-takiego")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Dokument nie istnieje."


def test_summary_with_unknown_doc_returns_404():
    resp = client.get("/api/summary/stream", params={"doc_ids": "brak1,brak2"})
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert "brak1" in detail and "brak2" in detail


def test_summary_without_docs_returns_400():
    resp = client.get("/api/summary/stream", params={"doc_ids": " , "})
    assert resp.status_code == 400
    assert "Nie wybrano" in resp.json()["detail"]


def test_upload_with_no_files_rejected():
    resp = client.post("/api/documents")
    assert resp.status_code in (400, 422)
