"""Wspólne fixture'y - client uruchamia lifespan aplikacji (składniki DI)."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
