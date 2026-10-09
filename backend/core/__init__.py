"""Jądro aplikacji - logika domenowa niezależna od FastAPI i infrastruktury.

Podmoduły:
- config        - Settings (.env) z walidacją
- exceptions    - hierarchia błędów domenowych
- logging       - konfiguracja structlog
- models        - modele danych (np. StoredDocument)
- chunking      - dzielenie dużych tekstów na części
- prompts       - prompty dla LLM
- ports/        - kontrakty (Protocol) na implementacje z adapters/
- services/     - orchestration (DocumentService, SummaryService)
"""
