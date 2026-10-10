"""Domain services (orchestration) - testable without HTTP.

- DocumentService - upload: validation -> extraction -> chunking -> store
- SummaryService  - map-reduce for large files + status/done/error event stream

FastAPI routers only wire these services to endpoints (thin controllers).
"""

from backend.core.services.documents import DocumentService, FileResult
from backend.core.services.summary import Event, SummaryService

__all__ = ["DocumentService", "Event", "FileResult", "SummaryService"]
