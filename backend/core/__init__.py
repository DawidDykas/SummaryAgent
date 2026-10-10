"""Application core - domain logic independent of FastAPI and infrastructure.

Submodules:
- config        - Settings (.env) with validation
- exceptions    - domain error hierarchy
- logging       - structlog configuration
- models        - data models (e.g. StoredDocument)
- chunking      - splitting large texts into chunks
- prompts       - prompts for the LLM
- ports/        - contracts (Protocol) implemented by adapters/
- services/     - orchestration (DocumentService, SummaryService)
"""
