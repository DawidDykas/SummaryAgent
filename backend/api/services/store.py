"""Kompatybilność wsteczna - implementacja żyje w backend.adapters.store."""

from backend.adapters.store import create_store
from backend.api.config import get_settings
from backend.core.models import StoredDocument

store = create_store(get_settings())

__all__ = ["StoredDocument", "store"]
