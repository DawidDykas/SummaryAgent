"""Serwisy domenowe (orchestration) - testowalne bez HTTP.

- DocumentService - upload: walidacja -> ekstrakcja -> chunking -> magazyn
- SummaryService  - map-reduce dla dużych plików + strumień zdarzeń status/done/error

Routery FastAPI tylko przepinają te serwisy do endpointów (thin controllers).
"""

from backend.core.services.documents import DocumentService, FileResult
from backend.core.services.summary import Event, SummaryService

__all__ = ["DocumentService", "Event", "FileResult", "SummaryService"]
