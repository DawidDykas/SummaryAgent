"""Testy konfiguracji - walidacja i przełączanie providerów."""

import pytest
from pydantic import ValidationError

from backend.core.config import Settings


def test_defaults_use_ollama():
    s = Settings(_env_file=None)
    assert s.provider == "ollama"
    assert s.active_model == "llama3.2"
    assert s.active_label.startswith("Ollama")
    assert s.active_base_url == "http://localhost:11434"


def test_external_api_wins_when_url_set():
    s = Settings(_env_file=None, llm_api_url="https://api.openai.com/v1/")
    assert s.provider == "external"
    assert s.active_model == "gpt-4o-mini"
    assert s.active_base_url == "https://api.openai.com/v1"
    assert s.active_label == "API · gpt-4o-mini"


def test_env_vars_are_read(monkeypatch):
    monkeypatch.setenv("LLM_API_URL", "https://example.com/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    s = Settings(_env_file=None)
    assert s.provider == "external"
    assert s.active_model == "test-model"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chunk_size": 50},  # za małe
        {"chunk_overlap": 500, "chunk_size": 400},  # overlap >= size
        {"summary_concurrency": 0},
        {"summary_concurrency": 9},
        {"max_files": 0},
        {"max_file_size_mb": 0},
        {"doc_ttl_seconds": 0},
        {"summary_temperature": 3.0},
        {"max_retries": -1},
    ],
)
def test_invalid_settings_rejected(kwargs):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **kwargs)


def test_unknown_env_vars_ignored():
    s = Settings(_env_file=None, _extra_unknown="whatever")
    assert s.provider == "ollama"
