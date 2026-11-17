"""Leak tests: raw OTPs, card numbers, passwords, PINs, CVVs and Aadhaar numbers must never appear in
the database, in any API response, or in any log line, including on error paths (blueprint §5.5)."""
import json
import logging
import random
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.core.errors import VigilException
from backend.app.main import app
from backend.app.models.models import Evidence, Incident, Redaction, Utterance
from backend.app.schemas.schemas import EvidenceCreate, IncidentCreate
from backend.app.services import incident_service
from backend.app.services.incident_service import create_incident
from backend.tests.test_redaction import make_aadhaar

AADHAAR = make_aadhaar(random.Random(11))
AADHAAR_FMT = f"{AADHAAR[:4]} {AADHAAR[4:8]} {AADHAAR[8:]}"

# Strings that must never be stored, returned or logged. Short secrets (PIN/CVV) are checked together
# with their cue because 3-4 digits can legitimately occur inside timestamps or hashes.
SECRETS = [
    "482913", "4111111111111111", "4111 1111 1111 1111", "08/27", "Hunter@2026x",
    AADHAAR, AADHAAR_FMT, "PIN 7391", "CVV 829",
]

UPI = "verify-cbi@okhdfcbank"
EVIDENCE_TEXT = (
    f"Pay the fee to {UPI} or call +91 98765 43210. Your OTP is 482913. "
    "Card 4111 1111 1111 1111 exp 08/27 CVV 829. Share your UPI PIN 7391. "
    f"Aadhaar {AADHAAR_FMT}. My password is Hunter@2026x."
)


def payload(title="Caller asked for OTP 482913", text=EVIDENCE_TEXT):
    return {
        "title": title,
        "source_channel": "call",
        "language": "en",
        "evidence": [{
            "type": "transcript",
            "text": text,
            "provenance": "pasted by user; password is Hunter@2026x",
            "speaker_turns": [
                {"speaker": "caller", "text": "Tell me the OTP you received"},
                {"speaker": "victim", "text": "482913"},
                {"speaker": "caller", "text": f"Now the card {'4111111111111111'} and aadhaar {AADHAAR}"},
            ],
        }],
    }


def assert_clean(blob: str, where: str):
    for secret in SECRETS:
        assert secret not in blob, f"raw secret {secret!r} leaked into {where}"


def db_dump(session_factory) -> str:
    engine = session_factory.kw["bind"]
    with engine.connect() as conn:
        return "\n".join(conn.connection.driver_connection.iterdump())


def everything_logged(caplog, capfd) -> str:
    out, err = capfd.readouterr()
    return caplog.text + out + err


@pytest.fixture
def logs(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog


def test_secrets_never_reach_db_responses_or_logs(client, session_factory, logs, capfd):
    responses = []

    def keep(resp):
        assert resp.status_code == 200, resp.text
        responses.append(resp.text)
        return resp.json()

    first = keep(client.post("/api/v1/incidents", json=payload()))
    second = keep(client.post("/api/v1/incidents", json=payload(title="Second call", text=EVIDENCE_TEXT)))
    keep(client.post(f"/api/v1/incidents/{first['id']}/evidence", json={
        "type": "message", "text": "Also OTP 482913 and password: Hunter@2026x", "provenance": "user_paste"}))
    keep(client.post(f"/api/v1/analyze/{first['id']}"))
    keep(client.get(f"/api/v1/incidents/{first['id']}"))
    keep(client.get(f"/api/v1/incidents/{second['id']}"))
    keep(client.get("/api/v1/incidents"))
    graph = keep(client.get("/api/v1/graph"))
    for edge in graph["edges"]:
        if edge["id"].startswith("assoc_"):
            keep(client.get(f"/api/v1/associations/{edge['id'].split('_')[1]}"))

    # The two incidents share an identifier, so the inspector payload was exercised too.
    assert any(e["id"].startswith("assoc_") for e in graph["edges"])

    # 1) API responses
    assert_clean("\n".join(responses), "an API response")

    # 2) The whole database, every table
    dump = db_dump(session_factory)
    assert_clean(dump, "the database dump")

    # 3) Logs and stdout/stderr (DEBUG level for every logger)
    assert_clean(everything_logged(logs, capfd), "the logs")

    # Redaction was selective: matching identifiers are kept, secrets are not
    assert UPI in dump and "+919876543210" in dump
    assert "[REDACTED:OTP]" in dump and "[REDACTED:CARD]" in dump and "[REDACTED:AADHAAR]" in dump

    # The API tells the user what was removed (counts only)
    kinds = {r["kind"] for r in first["redactions"]}
    assert {"OTP", "CARD", "CARD_EXPIRY", "CVV", "PIN", "PASSWORD", "AADHAAR"} <= kinds

    # Audit rows exist and hold no secret values
    with session_factory() as db:
        rows = db.query(Redaction).all()
        assert rows and all(r.detector_version.startswith("redact@") for r in rows)
        assert {"text", "title", "provenance"} <= {r.field for r in rows}
        assert any(r.field.startswith("turn:") for r in rows)
        assert any(r.field == "title" and r.evidence_id is None for r in rows)


def test_hash_is_of_the_stored_redacted_text(client, session_factory):
    from ai_engine.extraction.normalisation import compute_sha256
    client.post("/api/v1/incidents", json=payload())
    with session_factory() as db:
        ev = db.query(Evidence).one()
        assert ev.sha256 == compute_sha256(ev.original_text)
        assert "482913" not in ev.original_text and "482913" not in ev.normalised_text


def test_validation_error_path_does_not_echo_or_log_secrets(client, session_factory, logs, capfd):
    # Empty title fails validation while the body still carries secrets.
    resp = client.post("/api/v1/incidents", json=payload(title=""))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert_clean(resp.text, "the 422 body")

    # Over-long evidence containing a secret at the end
    too_long = "x " * 10_001 + "OTP is 482913"
    resp = client.post("/api/v1/incidents", json=payload(text=too_long))
    assert resp.status_code == 422
    assert_clean(resp.text, "the 422 body (too long)")

    assert_clean(everything_logged(logs, capfd), "the logs after validation errors")
    assert_clean(db_dump(session_factory), "the database after rejected requests")


def test_server_error_path_does_not_leak_secrets(client, session_factory, logs, capfd, monkeypatch):
    seen = {}

    def crashing_extractor(text):
        seen["text"] = text
        raise RuntimeError(f"extractor crashed on: {text}")  # worst case: the error message embeds the text

    monkeypatch.setattr(incident_service, "extract_entities", crashing_extractor)
    quiet_client = TestClient(app, raise_server_exceptions=False)  # keeps the dependency override from `client`
    resp = quiet_client.post("/api/v1/incidents", json=payload())

    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert_clean(resp.text, "the 500 body")
    # The extractor only ever saw redacted text, so even this worst-case error message and its log are clean.
    assert "[REDACTED:OTP]" in seen["text"]
    assert_clean(everything_logged(logs, capfd), "the logs after a server error")
    assert_clean(db_dump(session_factory), "the database after a server error")


def test_schema_redaction_fails_closed(client, session_factory, monkeypatch):
    from backend.app.schemas import schemas

    def broken(*args, **kwargs):
        raise RuntimeError("detector crashed")

    monkeypatch.setattr(schemas, "redact_evidence", broken)
    resp = client.post("/api/v1/incidents", json=payload())
    assert resp.status_code == 422
    assert "nothing was stored" in resp.json()["error"]["message"]
    with session_factory() as db:
        assert db.query(Incident).count() == 0 and db.query(Evidence).count() == 0


def test_service_redaction_fails_closed_and_stores_nothing(session_factory, monkeypatch):
    data = IncidentCreate(**payload())  # validates and redacts normally

    def broken(*args, **kwargs):
        raise RuntimeError("detector crashed")

    monkeypatch.setattr(incident_service, "redact_evidence", broken)
    with session_factory() as db:
        with pytest.raises(VigilException) as exc:
            create_incident(db, data)
        assert exc.value.code == "REDACTION_FAILED"
        assert db.query(Incident).count() == 0
        assert db.query(Evidence).count() == 0
        assert db.query(Utterance).count() == 0
        assert db.query(Redaction).count() == 0


def test_service_backup_redacts_when_schema_validation_is_bypassed(session_factory):
    # model_construct skips validators entirely: the service layer must still never store a secret.
    ev = EvidenceCreate.model_construct(
        type="transcript", text=EVIDENCE_TEXT, timestamp=None, provenance="password is Hunter@2026x",
        speaker_turns=[{"speaker": "victim", "text": "OTP 482913"}],
    )
    inc = IncidentCreate.model_construct(
        title="OTP 482913 incident", source_channel="call", language="en", notes=None,
        scenario_id=None, evidence=[ev],
    )
    with session_factory() as db:
        create_incident(db, inc)
        assert db.query(Redaction).count() > 0
    assert_clean(db_dump(session_factory), "the database (validation bypassed)")


def test_static_demo_data_contains_no_secrets():
    demo = Path(__file__).resolve().parents[2] / "frontend" / "public" / "demo-data"
    from ai_engine.privacy.redaction import redact_text

    def strings(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for v in node.values():
                yield from strings(v)
        elif isinstance(node, list):
            for v in node:
                yield from strings(v)

    files = list(demo.glob("*.json"))
    assert files
    for f in files:
        for s in strings(json.loads(f.read_text(encoding="utf-8"))):
            assert redact_text(s).text == s, f"{f.name} contains a redactable value: {s[:60]!r}"
