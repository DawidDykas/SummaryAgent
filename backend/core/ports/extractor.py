"""Port (interface) for extracting text from a file.

Implementation: the registry in `backend/adapters/extractors/` (called by
DocumentService as a plain callable).

Note: the method body is intentionally empty `...` - this is a *contract*,
not missing code.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TextExtractor(Protocol):
    """Callable: (file name, bytes) -> (format, text)."""

    def __call__(self, file_name: str, data: bytes) -> tuple[str, str]:
        """Return ``(format, text)``.

        Implementations raise `backend.core.exceptions.ExtractionError`
        for unsupported formats and read errors.
        """
        ...
