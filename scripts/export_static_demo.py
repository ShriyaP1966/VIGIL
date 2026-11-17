#!/usr/bin/env python3
"""
Precomputed synthetic demo data exporter (blueprint §14).

Runs the REAL pipeline: seeds the synthetic incidents into an in-memory database, calls the actual
FastAPI endpoints, and writes the responses into frontend/public/demo-data/ so the public static
site works even when the free backend is asleep. Nothing here is hand-written: every value
(risk score, hashes, entity ids, spans, contributions) is produced by the same code the live API uses.

Usage:  python scripts/export_static_demo.py
"""

import json
import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
os.environ["DATABASE_URL"] = "sqlite://"  # throwaway DB for the import-time create_all; no file is created

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.app.core.database import Base, get_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import models  # noqa: E402,F401  (register tables)
from backend.app.services.seed_service import seed_session  # noqa: E402

OUTPUT_DIR = root_dir / "frontend" / "public" / "demo-data"


def _write(name: str, payload) -> None:
    (OUTPUT_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def export() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with SessionLocal() as db:
            seed_session(db)

        client = TestClient(app)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Exporting real pipeline output to {OUTPUT_DIR} ...")

        incidents = client.get("/api/v1/incidents").json()
        incidents.sort(key=lambda i: i["id"])
        _write("incidents.json", incidents)

        graph = client.get("/api/v1/graph").json()
        _write("graph.json", graph)

        for inc in incidents:
            _write(f"incident_{inc['id']}.json", client.get(f"/api/v1/incidents/{inc['id']}").json())

        assoc_ids = sorted(int(e["id"].split("_", 1)[1]) for e in graph["edges"] if e["id"].startswith("assoc_"))
        for assoc_id in assoc_ids:
            _write(f"association_{assoc_id}.json", client.get(f"/api/v1/associations/{assoc_id}").json())

        _write("meta.json", {
            "synthetic": True,
            "generated_by": "scripts/export_static_demo.py",
            "note": "Precomputed from the real pipeline on synthetic seed data. Not real incidents.",
            "incidents": len(incidents),
            "associations": len(assoc_ids),
        })
        print(f"Done: {len(incidents)} incidents, {len(assoc_ids)} association(s).")
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    export()
