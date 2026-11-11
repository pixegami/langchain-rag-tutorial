"""API-layer tests. The services are stubbed, so these need no OpenAI, Chroma, Neo4j or WSD service."""
import urllib.error

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import ServiceError, symbolic_service, vector_service


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ingest_vector(client, monkeypatch):
    monkeypatch.setattr(vector_service, "ingest", lambda: None)
    response = client.post("/api/v1/ingest/vector")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_ingest_vector_script_failure_returns_500(client, monkeypatch):
    def boom():
        raise RuntimeError("chroma exploded")

    monkeypatch.setattr(vector_service, "ingest", boom)
    response = client.post("/api/v1/ingest/vector")
    assert response.status_code == 500
    assert "chroma exploded" in response.json()["detail"]


def test_ingest_symbolic_passes_limit_and_reports_counts(client, monkeypatch):
    calls = {}

    def fake_ingest(limit=None):
        calls["limit"] = limit
        return {"chunks_total": 5, "chunks_inserted": 4, "senses_processed": 12, "failed_chunks": ["alice-3"]}

    monkeypatch.setattr(symbolic_service, "ingest", fake_ingest)
    response = client.post("/api/v1/ingest/symbolic", json={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert calls["limit"] == 5
    assert body["chunks_inserted"] == 4
    assert body["failed_chunks"] == ["alice-3"]


def test_ingest_symbolic_without_body(client, monkeypatch):
    monkeypatch.setattr(
        symbolic_service,
        "ingest",
        lambda limit=None: {"chunks_total": 0, "chunks_inserted": 0, "senses_processed": 0, "failed_chunks": []},
    )
    assert client.post("/api/v1/ingest/symbolic").status_code == 200


def test_ingest_already_running_returns_409(client):
    assert vector_service._ingest_lock.acquire(blocking=False)
    try:
        assert client.post("/api/v1/ingest/vector").status_code == 409
    finally:
        vector_service._ingest_lock.release()


def test_query_vector(client, monkeypatch):
    monkeypatch.setattr(
        vector_service,
        "query",
        lambda q: {"found": True, "answer": "At a tea party.", "sources": ["data/books/alice_in_wonderland.md"]},
    )
    response = client.post("/api/v1/query/vector", json={"query": "How does Alice meet the Mad Hatter?"})
    assert response.status_code == 200
    assert response.json()["answer"] == "At a tea party."


def test_query_vector_no_match(client, monkeypatch):
    monkeypatch.setattr(vector_service, "query", lambda q: {"found": False, "answer": None, "sources": []})
    body = client.post("/api/v1/query/vector", json={"query": "unrelated"}).json()
    assert body["found"] is False and body["answer"] is None


@pytest.mark.parametrize("payload", [{}, {"query": ""}, {"q": "wrong field"}])
def test_query_validation(client, payload):
    assert client.post("/api/v1/query/vector", json=payload).status_code == 422
    assert client.post("/api/v1/query/symbolic", json=payload).status_code == 422


def test_query_symbolic(client, monkeypatch):
    monkeypatch.setattr(
        symbolic_service,
        "query",
        lambda q: {
            "found": True,
            "answer": "A hatter at the tea party.",
            "sources": ["alice_in_wonderland.md (alice_in_wonderland-3)"],
            "synsets": [{"surface": "Mad Hatter", "synset_id": "Q1234"}],
        },
    )
    response = client.post("/api/v1/query/symbolic", json={"query": "Who is the Mad Hatter?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "A hatter at the tea party."
    assert body["synsets"][0]["synset_id"] == "Q1234"


def test_query_symbolic_wsd_down_returns_502(client, monkeypatch):
    class FakeModule:
        @staticmethod
        def link_entities(_):
            raise urllib.error.URLError("connection refused")

        @staticmethod
        def to_senses(result):
            return []

    monkeypatch.setattr(symbolic_service, "_load_symbolic_link_data", lambda: FakeModule)
    response = client.post("/api/v1/query/symbolic", json={"query": "anything"})
    assert response.status_code == 502


def test_missing_config_returns_500_instead_of_killing_server(client, monkeypatch):
    def missing_url():
        raise ServiceError("SYMBOLIC_WSD_URL is not set.")

    monkeypatch.setattr(symbolic_service, "_load_symbolic_link_data", missing_url)
    response = client.post("/api/v1/query/symbolic", json={"query": "anything"})
    assert response.status_code == 500
    assert "SYMBOLIC_WSD_URL" in response.json()["detail"]
