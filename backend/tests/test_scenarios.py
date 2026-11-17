"""Scenario Lab API: deterministic replays through the real pipeline in an isolated database."""
import pytest

from backend.app.services import scenario_service as svc

ADJUSTABLE = {"digital_arrest_cbi", "digital_arrest_customs", "bank_kyc_link", "courier_customs_parcel"}


@pytest.fixture(scope="module")
def runs():
    """One replay of every scenario at the default rotation (shared by the tests below)."""
    return {s.name: svc.run_scenario(s.name) for s in svc.SCENARIOS}


def test_list_has_between_10_and_12_scenarios_covering_the_blueprint_categories(client):
    r = client.get("/api/v1/scenarios")
    assert r.status_code == 200
    items = r.json()
    assert 10 <= len(items) <= 12
    assert len({i["name"] for i in items}) == len(items)
    assert {"positive", "negative", "ambiguous", "decoy", "injection", "counter_evidence"} <= {i["category"] for i in items}
    assert {i["name"] for i in items if i["rotation_adjustable"]} == ADJUSTABLE
    assert all(i["default_rotation"] == 0.5 for i in items if i["rotation_adjustable"])


def test_every_scenario_reports_checks_invariants_and_the_synthetic_disclaimer(runs):
    for name, run in runs.items():
        assert run["name"] == name and run["seed"] == svc.SCENARIO_SEED
        assert "synthetic" in run["disclaimer"].lower() and "hypothesis" in run["disclaimer"]
        assert run["incidents"] and isinstance(run["matches_expected"], bool)
        names = [c["name"] for c in run["checks"]]
        assert any(n.startswith("I1") for n in names) and any(n.startswith("I4") for n in names)
        for inv in (c for c in run["checks"] if c["name"][:2] in ("I1", "I2", "I4")):
            assert inv["passed"] is True, f"{name}: {inv['name']}"
        assert all(c["passed"] in (True, False, None) for c in run["checks"])


def test_rotation_only_affects_the_campaign_scenarios(runs):
    for name, run in runs.items():
        assert (run["rotation"] == 0.5) == (name in ADJUSTABLE)
    assert svc.run_scenario("legitimate_notices", 0.9)["rotation"] is None     # ignored, reported as null


def test_a_campaign_at_rotation_zero_links_by_identifier_and_at_one_only_by_behaviour():
    zero = svc.run_scenario("digital_arrest_cbi", 0.0)
    assert zero["summary"]["observed_links"] == 3 and zero["matches_expected"] is True
    assert any(h for h in zero["hypotheses"] if len(h["members"]) == 3)
    one = svc.run_scenario("digital_arrest_cbi", 1.0)
    assert one["summary"]["observed_links"] == 0                                 # every identifier rotated
    assert all(link["status"] != "OBSERVED_MATCH" for link in one["links"])      # I2: behaviour never makes one
    assert all(h["status"] == "HYPOTHESIS_UNREVIEWED" for h in one["hypotheses"])


def test_expected_identifier_links_come_from_what_each_text_actually_mentions():
    """A bank-KYC SMS may leave the link out of its text, so it cannot share the domain even at rotation 0."""
    for r in (0.0, 0.5, 1.0):
        run = svc.run_scenario("bank_kyc_link", r)
        records = svc.BY_NAME["bank_kyc_link"].build(r)
        assert run["summary"]["observed_links"] == svc._sharing_pairs(records)
        assert run["matches_expected"] is True


def test_a_scenario_is_deterministic():
    assert svc.run_scenario("bank_kyc_link", 0.5) == svc.run_scenario("bank_kyc_link", 0.5)
    assert svc.run_scenario("benign_helpline_overlap") == svc.run_scenario("benign_helpline_overlap")


def test_benign_helpline_links_are_disputed_not_observed(runs):
    run = runs["benign_helpline_overlap"]
    assert run["summary"]["observed_links"] == 0 and run["summary"]["disputed_links"] >= 1
    assert run["matches_expected"] is True


def test_injection_scenario_flags_the_attack_without_changing_labels_or_lowering_risk(runs):
    run = runs["prompt_injection"]
    by_id = {i["id"]: i for i in run["incidents"]}
    assert by_id["inj_attacked"]["injection_flags"] and not by_id["inj_clean"]["injection_flags"]
    assert by_id["inj_attacked"]["detected_labels"] == by_id["inj_clean"]["detected_labels"]
    assert by_id["inj_attacked"]["risk"]["score"] >= by_id["inj_clean"]["risk"]["score"]
    assert run["matches_expected"] is True


def test_api_run_unknown_name_and_bad_rotation(client):
    r = client.post("/api/v1/scenarios/no_such_scenario/run")
    assert r.status_code == 404 and "error" in r.json()
    r = client.post("/api/v1/scenarios/digital_arrest_cbi/run", json={"rotation": 1.5})
    assert r.status_code == 422
    r = client.post("/api/v1/scenarios/digital_arrest_cbi/run", json={"rotation": -0.1})
    assert r.status_code == 422


def test_api_run_matches_the_service_and_never_stores_anything(client):
    before = client.get("/api/v1/incidents").json()
    r = client.post("/api/v1/scenarios/digital_arrest_cbi/run", json={"rotation": 0.0})
    assert r.status_code == 200 and r.json() == svc.run_scenario("digital_arrest_cbi", 0.0)
    assert client.post("/api/v1/scenarios/digital_arrest_cbi/run").json()["rotation"] == 0.5    # default, no body
    assert client.get("/api/v1/incidents").json() == before                      # the real database is untouched
    assert client.get("/api/v1/campaigns").json() == []
