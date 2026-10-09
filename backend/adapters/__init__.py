"""Implementacje portów z `backend/core/ports` + fabryki wyboru.

- llm/        - LLMClient: OpenAI-compat, Ollama (+ retry) - wybiera create_llm_client()
- store/      - DocumentStore: in-memory - wybiera create_store()
- extractors/ - TextExtractor: rejestr formatów (PDF, DOCX, HTML, RTF, TXT, MD)
"""
