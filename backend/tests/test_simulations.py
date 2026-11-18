"""Simulated live call analysis: scripted transcripts, text only, nothing stored."""
import json
from pathlib import Path

import pytest

from backend.app.services import scenario_service, simulation_service as svc

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "frontend" / "public" / "demo-data"


def window(script, n):
    return [{"speaker": s, "text": t} for s, t in script["utterances"][:n]]


@pytest.fixture(scope="module")
def frames():
    """Every script analysed after every turn (the same thing the static export stores)."""
    return {s["name"]: [svc.analyze_window(window(s, n), s["language"]) for n in range(1, len(s["utterances"]) + 1)]
            for s in svc.SCRIPTS}


def test_scripts_are_listed_with_their_transcripts(client):
    items = client.get("/api/v1/simulations").json()
    assert {i["name"] for i in items} == {"digital_arrest_en", "digital_arrest_hinglish", "injection_attempt", "genuine_bank_call"}
    assert all(i["turns"] == len(i["utterances"]) >= 4 for i in items)


def test_stages_light_up_in_sequence_and_never_go_dark_again(frames):
    for name, fs in frames.items():
        reached = [{s["stage"] for s in f["stages"] if s["reached"]} for f in fs]
        for earlier, later in zip(reached, reached[1:]):
            assert earlier <= later, f"{name}: a stage that was reached disappeared"
        assert [f["turns"] for f in fs] == list(range(1, len(fs) + 1))


def test_a_digital_arrest_call_climbs_to_all_six_stages_and_a_high_band(frames):
    for name in ("digital_arrest_en", "digital_arrest_hinglish"):
        last = frames[name][-1]
        assert [s["stage"] for s in last["stages"] if s["reached"]] == ["AUTHORITY", "ALLEGATION", "THREAT", "ISOLATION", "URGENCY", "DEMAND"]
        assert last["risk"]["band"] in ("HIGH", "CRITICAL")
        scores = [f["risk"]["score"] for f in frames[name]]
        assert scores == sorted(scores)                                   # in these scripts risk only rises
        assert sum(c["contribution"] for c in last["risk"]["contributions"]) == last["risk"]["score"]


def test_the_genuine_call_stays_low(frames):
    last = frames["genuine_bank_call"][-1]
    assert last["risk"]["band"] == "LOW" and not any(s["reached"] for s in last["stages"])
    assert last["guidance"]["en"] == [svc.CALM[0]]


def test_injection_fires_the_badge_and_the_risk_does_not_fall(frames):
    script = svc.BY_NAME["injection_attempt"]
    last = frames["injection_attempt"][-1]
    assert last["injection_flags"] and any(u["injection_spans"] for u in last["utterances"])
    clean = [u for u in script["utterances"] if "Ignore all previous" not in u[1]]
    clean_frame = svc.analyze_window([{"speaker": s, "text": t} for s, t in clean], "en")
    assert not clean_frame["injection_flags"]
    assert last["risk"]["score"] >= clean_frame["risk"]["score"]          # an injected instruction can never lower it
    assert any("ignored" in c for c in last["guidance"]["en"])


def test_guidance_has_english_and_hindi_cards_and_the_disclaimer(frames):
    for fs in frames.values():
        for f in fs:
            g = f["guidance"]
            assert g["en"] and len(g["en"]) == len(g["hi"])
            assert "does not intercept or listen to real calls" in f["disclaimer"]
            assert "real-time call protection" not in json.dumps(f).lower()
    assert any(ch > "ऀ" for ch in frames["digital_arrest_en"][-1]["guidance"]["hi"][0])    # Devanagari


def test_api_validation_and_redaction(client):
    assert client.post("/api/v1/simulations/live-call/analyze", json={"utterances": []}).status_code == 422
    too_many = [{"speaker": "caller", "text": "hello"}] * (svc.MAX_TURNS + 1)
    assert client.post("/api/v1/simulations/live-call/analyze", json={"utterances": too_many}).status_code == 422
    long_turn = [{"speaker": "caller", "text": "x" * (svc.MAX_TURN_CHARS + 1)}]
    assert client.post("/api/v1/simulations/live-call/analyze", json={"utterances": long_turn}).status_code == 422
    r = client.post("/api/v1/simulations/live-call/analyze",
                    json={"utterances": [{"speaker": "caller", "text": "Your OTP is 482913, read it out now."}]})
    assert r.status_code == 200 and "482913" not in json.dumps(r.json())


def test_analysis_stores_nothing_in_the_application_database(client):
    before = client.get("/api/v1/incidents").json()
    s = svc.SCRIPTS[0]
    client.post("/api/v1/simulations/live-call/analyze", json={"utterances": window(s, 5)})
    assert client.get("/api/v1/incidents").json() == before == []


def test_committed_static_frames_are_what_the_endpoint_produces(frames):
    for name in ("injection_attempt", "genuine_bank_call"):
        committed = json.loads((DEMO / f"simulation_{name}.json").read_text(encoding="utf-8"))
        assert committed["frames"] == frames[name], f"{name}: run python scripts/export_static_demo.py"
    scripts = json.loads((DEMO / "simulations.json").read_text(encoding="utf-8"))
    assert scripts == svc.list_scripts()


def test_committed_static_scenarios_are_what_the_service_produces():
    committed = json.loads((DEMO / "scenario_digital_arrest_cbi__r50.json").read_text(encoding="utf-8"))
    assert committed == scenario_service.run_scenario("digital_arrest_cbi", 0.5)
    listing = json.loads((DEMO / "scenarios.json").read_text(encoding="utf-8"))
    assert listing == scenario_service.list_scenarios()
    for sc in listing:
        names = ([f"scenario_{sc['name']}__r{p}.json" for p in (0, 25, 50, 75, 100)]
                 if sc["rotation_adjustable"] else [f"scenario_{sc['name']}.json"])
        assert all((DEMO / n).exists() for n in names), sc["name"]
