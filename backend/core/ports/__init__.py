"""Contracts (interfaces) between the core and the infrastructure.

Port methods have intentionally empty bodies (`...`) - these are *contract
declarations*, not unfinished implementations. Real code lives in
`backend/adapters/*`:

- LLMClient      -> backend/adapters/llm/   (OpenAI-compat, Ollama)
- DocumentStore  -> backend/adapters/store/ (in-memory; Redis/DB later)
- TextExtractor  -> backend/adapters/extractors/ (registry: PDF, DOCX, ...)

This way the core depends on the *interface* and swapping implementations
never touches the business logic.
"""

from backend.core.ports.extractor import TextExtractor
from backend.core.ports.llm import LLMClient, Message
from backend.core.ports.store import DocumentStore

__all__ = ["DocumentStore", "LLMClient", "Message", "TextExtractor"]
