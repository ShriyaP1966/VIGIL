from fastapi.testclient import TestClient

from backend.app import main as app_main
from backend.app.core.config import settings
from backend.app.core.database import get_db


def _client_with_db(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_main.app.dependency_overrides[get_db] = override_get_db
    return TestClient(app_main.app)


def test_startup_seed_populates_empty_database_once(session_factory, monkeypatch):
    monkeypatch.setattr(settings, "SEED_ON_START", True)
    monkeypatch.setattr(app_main, "SessionLocal", session_factory)
    try:
        for _ in range(2):  # a second cold start must not duplicate the seed data
            with _client_with_db(session_factory) as client:
                incidents = client.get("/api/v1/incidents").json()
                assert len(incidents) == 3
                edges = [e for e in client.get("/api/v1/graph").json()["edges"] if e["id"].startswith("assoc_")]
                assert len(edges) == 1 and edges[0]["status"] == "OBSERVED_MATCH"
    finally:
        app_main.app.dependency_overrides.clear()


def test_no_seed_by_default(session_factory, monkeypatch):
    monkeypatch.setattr(settings, "SEED_ON_START", False)
    monkeypatch.setattr(app_main, "SessionLocal", session_factory)
    try:
        with _client_with_db(session_factory) as client:
            assert client.get("/api/v1/incidents").json() == []
    finally:
        app_main.app.dependency_overrides.clear()
