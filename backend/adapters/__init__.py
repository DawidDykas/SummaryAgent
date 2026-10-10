"""Implementations of `backend/core/ports` + selection factories.

- llm/        - LLMClient: OpenAI-compat, Ollama (+ retry) - picked by create_llm_client()
- store/      - DocumentStore: in-memory - picked by create_store()
- extractors/ - TextExtractor: format registry (PDF, DOCX, HTML, RTF, TXT, MD)
"""
