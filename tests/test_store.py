"""Tests for the document store (in-memory adapter)."""

import time

from backend.adapters.store import InMemoryDocumentStore, create_store
from backend.core.config import Settings
from backend.core.models import StoredDocument
from backend.core.ports.store import DocumentStore


def test_create_store_returns_port_implementation():
    store = create_store(Settings(_env_file=None, doc_ttl_seconds=123))
    assert isinstance(store, DocumentStore)
    assert isinstance(store, InMemoryDocumentStore)


def test_put_get_delete_roundtrip():
    store = InMemoryDocumentStore(ttl_seconds=3600)
    doc = store.put(name="a.txt", fmt="TXT", text="Ala ma kota", chunks=1)

    assert isinstance(doc, StoredDocument)
    assert doc.chars == len("Ala ma kota")
    assert doc.words == 3
    assert len(doc.id) == 12

    assert store.get(doc.id) is doc
    assert store.delete(doc.id) is True
    assert store.get(doc.id) is None
    assert store.delete(doc.id) is False


def test_ids_are_unique():
    store = InMemoryDocumentStore()
    ids = {store.put(f"{i}.txt", "TXT", "x", 1).id for i in range(50)}
    assert len(ids) == 50


def test_expired_documents_are_dropped():
    store = InMemoryDocumentStore(ttl_seconds=1)
    doc = store.put("old.txt", "TXT", "tekst", 1)
    doc.created_at = time.time() - 10  # simulate age

    assert store.get(doc.id) is None
    assert store.delete(doc.id) is False


def test_put_cleans_expired_entries():
    store = InMemoryDocumentStore(ttl_seconds=1)
    old = store.put("old.txt", "TXT", "tekst", 1)
    old.created_at = time.time() - 10

    fresh = store.put("new.txt", "TXT", "tekst", 1)
    assert store.get(old.id) is None
    assert store.get(fresh.id) is fresh
