"""Port (interface) for the LLM client.

Implementations: `backend/adapters/llm/openai.py` and
`backend/adapters/llm/ollama.py`, selected by the factory
`backend.adapters.llm.create_llm_client()`.

Note: method bodies are intentionally empty `...` - these are *contracts*,
not missing code.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

Message = dict[str, str]


@runtime_checkable
class LLMClient(Protocol):
    """Contract shared by Ollama and OpenAI-compatible APIs."""

    async def chat(self, messages: list[Message], *, max_tokens: int = 1600) -> str:
        """Return the model's response content (non-streaming).

        Implementations raise `backend.core.exceptions.LLMError` on
        network, HTTP or empty-response errors.
        """
        ...

    async def close(self) -> None:
        """Release resources (HTTP connections) - called at app shutdown."""
        ...
