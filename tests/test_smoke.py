"""Testy smoke - podstawowe endpointy muszą działać."""

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["provider"] in {"ollama", "external"}
    assert "PDF" in data["supported_formats"]


def test_index_serves_ui():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "SummaryAgent" in resp.text


def test_ollama_status_shape():
    resp = client.get("/api/ollama/status")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) >= {"reachable", "base_url", "model", "model_ready", "models", "detail"}


def test_upload_and_delete_txt():
    resp = client.post(
        "/api/documents",
        files=[("files", ("notatka.txt", b"Ala ma kota. ", "text/plain"))],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert not body["errors"]
    assert len(body["documents"]) == 1
    doc = body["documents"][0]
    assert doc["format"] == "TXT"
    assert doc["chars"] > 0
    assert doc["chunks"] >= 1

    delete = client.delete(f"/api/documents/{doc['id']}")
    assert delete.status_code == 200
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 404


def test_upload_rejects_unsupported_format():
    resp = client.post(
        "/api/documents",
        files=[("files", ("program.exe", b"MZ", "application/octet-stream"))],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert not body["documents"]
    assert body["errors"][0]["name"] == "program.exe"


def test_summary_stream_requires_doc_ids():
    resp = client.get("/api/summary/stream", params={"doc_ids": "  ,  "})
    assert resp.status_code == 400
