"""Testy logowania i middleware request-id."""

import pytest
from pydantic import ValidationError

from backend.core.config import Settings
from backend.core.logging import setup_logging


def test_default_log_settings():
    s = Settings(_env_file=None)
    assert s.log_level == "INFO"
    assert s.log_json is False


def test_log_level_is_normalized_to_uppercase():
    s = Settings(_env_file=None, log_level="debug")
    assert s.log_level == "DEBUG"


def test_invalid_log_level_rejected():
    with pytest.raises(ValidationError, match="log_level"):
        Settings(_env_file=None, log_level="TRACE")


@pytest.mark.parametrize("fmt", [True, False])
def test_setup_logging_does_not_crash(fmt):
    setup_logging(Settings(_env_file=None, log_json=fmt, log_level="WARNING"))


def test_request_id_is_generated(client):
    resp = client.get("/api/health")
    assert resp.headers.get("x-request-id")
    assert len(resp.headers["x-request-id"]) == 12


def test_request_id_is_propagated(client):
    resp = client.get("/api/health", headers={"X-Request-ID": "moj-id-123"})
    assert resp.headers["x-request-id"] == "moj-id-123"


def test_request_id_on_static_and_index(client):
    assert client.get("/").headers.get("x-request-id")
    assert client.get("/static/app.js").headers.get("x-request-id")


def test_request_id_on_error_responses(client):
    resp = client.delete("/api/documents/brak")
    assert resp.status_code == 404
    assert resp.headers.get("x-request-id")
