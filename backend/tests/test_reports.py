"""Structured incident report: facts, inferences, analyst actions, counter-evidence and limitations kept apart."""
import csv
import io

import pytest

from backend.app.services import report_service
from backend.app.services.seed_service import seed_session


@pytest.fixture
def seeded(client, session_factory):
    with session_factory() as db:
        seed_session(db)
    return client


def test_report_has_the_five_separate_parts_and_is_synthetic(seeded):
    r = seeded.get("/api/v1/incidents/1/report")
    assert r.status_code == 200
    rep = r.json()
    assert rep["report_version"] == report_service.REPORT_VERSION and rep["synthetic"] is True
    for key in ("incident", "observed_facts", "model_inferences", "analyst_actions", "counter_evidence", "limitations"):
        assert key in rep
    assert rep["limitations"] and any("synthetic" in x.lower() for x in rep["limitations"])
    assert any("not a probability" in x for x in rep["limitations"])


def test_observed_matches_are_facts_and_behavioural_candidates_are_inferences(seeded):
    rep = seeded.get("/api/v1/incidents/1/report").json()
    assert rep["observed_facts"]["observed_matches"], "incidents 1 and 2 share an exact UPI handle"
    assert all(m["status"] == "OBSERVED_MATCH" for m in rep["observed_facts"]["observed_matches"])
    assert all(m["status"] == "CANDIDATE_ASSOCIATION" for m in rep["model_inferences"]["behavioural_candidates"])
    # a candidate never appears among the observed facts (I2) and vice versa
    observed_ids = {m["association_id"] for m in rep["observed_facts"]["observed_matches"]}
    assert not observed_ids & {m["association_id"] for m in rep["model_inferences"]["behavioural_candidates"]}
    assert all(m["explanation"] for m in rep["observed_facts"]["observed_matches"])          # I5


def test_risk_contributions_sum_exactly_to_the_score_and_are_marked_a_heuristic(seeded):
    for iid in (1, 2, 3):
        risk = seeded.get(f"/api/v1/incidents/{iid}/report").json()["model_inferences"]["risk"]
        assert sum(c["contribution"] for c in risk["contributions"]) == risk["score"]
        assert "not a probability" in risk["note"]


def test_report_never_contains_raw_evidence_text_or_unmasked_identifiers(seeded):
    rep = seeded.get("/api/v1/incidents/1/report").json()
    assert "original_text" not in str(rep) and "normalised_text" not in str(rep)
    inc = seeded.get("/api/v1/incidents/1").json()
    full_text = inc["evidence_items"][0]["original_text"]
    assert full_text not in str(rep)
    for ident in rep["observed_facts"]["identifiers"]:
        assert "verify-cbi@okhdfcbank" not in ident["display_value"]                      # masked form only


def test_counter_evidence_and_disputed_links_are_reported_next_to_the_facts(seeded):
    rep = seeded.get("/api/v1/incidents/3/report").json()          # a genuine notice that cites the public helpline
    ce = rep["counter_evidence"]
    assert ce["findings"] or ce["disputed_or_rejected_links"]
    assert all(f["explanation"] and f["rule_id"].startswith("CE-") for f in ce["findings"])


def test_an_analyst_decision_appears_under_analyst_actions(seeded):
    obs = seeded.get("/api/v1/incidents/1/report").json()["observed_facts"]["observed_matches"][0]
    seeded.post(f"/api/v1/associations/{obs['association_id']}/review", json={"decision": "ACCEPT", "note": "checked"})
    rep = seeded.get("/api/v1/incidents/1/report").json()
    assert any(a["decision"] == "ACCEPT" and a["note"] == "checked" and a["target_type"] == "association"
               for a in rep["analyst_actions"])


def test_unknown_incident_and_bad_format(seeded):
    assert seeded.get("/api/v1/incidents/9999/report").status_code == 404
    assert seeded.get("/api/v1/incidents/1/report?format=xml").status_code == 422


def test_csv_is_a_download_with_one_row_per_field(seeded):
    r = seeded.get("/api/v1/incidents/1/report?format=csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="vigil_report_incident_1.csv"' in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["section", "record", "field", "value"]
    sections = {row[0] for row in rows[1:]}
    assert {"incident", "observed_facts.evidence", "model_inferences.risk.contributions", "limitations"} <= sections
    assert all(len(row) == 4 for row in rows)


def test_csv_neutralises_spreadsheet_formulas_in_untrusted_text(client):
    client.post("/api/v1/incidents", json={"title": "=HYPERLINK(\"http://x.example\",\"click\")",
                                           "evidence": [{"text": "Caller: hello"}]})
    csv_text = client.get("/api/v1/incidents/1/report?format=csv").text
    rows = list(csv.reader(io.StringIO(csv_text)))
    title = next(r for r in rows if r[0] == "incident" and r[2] == "title")
    assert title[3].startswith("'=")                                # a leading quote makes it plain text
    assert all(not r[3].startswith(("=", "+", "@")) for r in rows[1:])


def test_safe_helper():
    for bad in ("=1+1", "+1", "-1", "@SUM", "\tcmd", "\rx"):
        assert report_service._safe(bad).startswith("'")
    assert report_service._safe("plain") == "plain" and report_service._safe(None) == ""
    assert report_service._safe(["=a"]) == '["=a"]'                 # JSON text, not a formula
