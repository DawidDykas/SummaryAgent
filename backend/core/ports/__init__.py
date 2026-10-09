"""Kontrakty (interfejsy) między jądrem a infrastrukturą.

Metody portów mają świadomie puste ciała (`...`) - to *deklaracje kontraktu*,
a nie niedokończone implementacje. Realne kodowanie siedzi w `backend/adapters/*`:

- LLMClient      -> backend/adapters/llm/   (OpenAI-compat, Ollama)
- DocumentStore  -> backend/adapters/store/ (in-memory; docelowo Redis/DB)
- TextExtractor  -> backend/adapters/extractors/ (rejestr: PDF, DOCX, ...)

Dzięki temu core zależy od *interfejsu*, a zmiana implementacji nie dotyka logiki.
"""

from backend.core.ports.extractor import TextExtractor
from backend.core.ports.llm import LLMClient, Message
from backend.core.ports.store import DocumentStore

__all__ = ["DocumentStore", "LLMClient", "Message", "TextExtractor"]
