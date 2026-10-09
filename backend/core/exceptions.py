"""Hierarchia wyjątków domenowych.

W warstwie API (backend/api) są one tłumaczone na odpowiedzi HTTP
przez exception handlery zarejestrowane w main.py - logika biznesowa
nie importuje FastAPI.
"""

from __future__ import annotations


class SummaryAgentError(Exception):
    """Baza wszystkich błędów domenowych."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BadRequestError(SummaryAgentError):
    status_code = 400
    code = "bad_request"


class DocumentNotFoundError(SummaryAgentError):
    status_code = 404
    code = "document_not_found"

    def __init__(self, doc_ids: list[str] | str, message: str | None = None) -> None:
        self.doc_ids = [doc_ids] if isinstance(doc_ids, str) else doc_ids
        if message is None:
            missing = ", ".join(self.doc_ids)
            message = f"Dokument(y) {missing} wygasł/y - wgraj pliki ponownie."
        super().__init__(message)


class ExtractionError(SummaryAgentError):
    """Błąd odczytu pliku (obsługiwany per-plik przy uploadzie)."""

    status_code = 422
    code = "extraction_failed"


class LLMError(SummaryAgentError):
    """Błąd komunikacji z modelem / API."""

    status_code = 502
    code = "llm_error"
