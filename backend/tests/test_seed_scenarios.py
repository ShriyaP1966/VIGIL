"""The seeded demo scenarios (blueprint Appendix B) produce the intended associations, counter-evidence and hypotheses."""
import json

import pytest

from backend.app.models.models import Analysis, Association, Campaign, CampaignMember, CounterEvidence, Entity, RiskContribution
from backend.app.services.seed_service import SEED_INCIDENTS, seed_session


@pytest.fixture
def seeded(session_factory):
    db = session_factory()
    ids = seed_session(db)
    yield db, ids
    db.close()


def assoc_between(db, a, b):
    return db.query(Association).filter(Association.incident_a_id == a, Association.incident_b_id == b).one()


def findings(db, assoc):
    return {c.rule_id: c for c in db.query(CounterEvidence).filter(CounterEvidence.association_id == assoc.id)}


def test_seed_shape_matches_the_scenarios():
    assert len(SEED_INCIDENTS) == 9
    assert [s.scenario_id for s in SEED_INCIDENTS][4:] == [
        "scenario_05_public_helpline", "scenario_06_chronology_forward", "scenario_07_chronology_reversed",
        "scenario_08_payment_a", "scenario_09_payment_b"]


def test_exactly_the_intended_associations_exist(seeded):
    db, _ = seeded
    got = sorted((a.incident_a_id, a.incident_b_id, a.status, a.match_type) for a in db.query(Association))
    assert got == [
        (1, 2, "OBSERVED_MATCH", "EXACT_IDENTIFIER"),
        (1, 4, "CANDIDATE_ASSOCIATION", "PLAYBOOK"),
        (3, 5, "DISPUTED_ASSOCIATION", "EXACT_IDENTIFIER"),
        (6, 7, "DISPUTED_ASSOCIATION", "EXACT_IDENTIFIER"),
        (8, 9, "OBSERVED_MATCH", "EXACT_IDENTIFIER"),
    ]


def test_adjusted_confidence_is_base_plus_impacts_everywhere(seeded):
    db, _ = seeded
    for a in db.query(Association):
        impacts = sum(c.confidence_impact for c in db.query(CounterEvidence).filter(CounterEvidence.association_id == a.id))
        assert a.adjusted_confidence == pytest.approx(max(0.0, min(1.0, a.base_confidence + impacts)))


def test_ce3_shared_public_helpline_is_disputed(seeded):
    db, _ = seeded
    a = assoc_between(db, 3, 5)
    f = findings(db, a)
    assert a.status == "DISPUTED_ASSOCIATION" and set(f) == {"CE-3", "CE-5"}
    assert (f["CE-3"].severity, f["CE-3"].confidence_impact) == ("HIGH", -0.40)
    assert "public identifier (National Cyber Crime Helpline)" in f["CE-3"].observation
    (entity,) = [db.query(Entity).get(i) for i in json.loads(a.shared_entity_ids_json)]
    assert (entity.type, entity.canonical_value, entity.display_value) == ("PHONE", "1930", "1930")
    assert {r["incident_id"] for r in json.loads(f["CE-3"].evidence_refs_json)} == {3, 5}
    assert a.adjusted_confidence == pytest.approx(0.70 - 0.40 - 0.10)


def test_ce1_chronology_inversion_is_disputed(seeded):
    db, _ = seeded
    a = assoc_between(db, 6, 7)
    f = findings(db, a)
    assert a.status == "DISPUTED_ASSOCIATION" and set(f) == {"CE-1"}
    assert (f["CE-1"].severity, f["CE-1"].confidence_impact) == ("HIGH", -0.30)
    assert "4 shared stages" in f["CE-1"].observation and "0%" in f["CE-1"].observation
    assert a.adjusted_confidence == pytest.approx(0.75 - 0.30)
    refs = json.loads(f["CE-1"].evidence_refs_json)
    assert {r["incident_id"] for r in refs} == {6, 7} and all(r["excerpt"] for r in refs)


def test_ce2_conflicting_payment_destinations_reduce_confidence_but_do_not_dispute(seeded):
    db, _ = seeded
    a = assoc_between(db, 8, 9)
    f = findings(db, a)
    assert a.status == "OBSERVED_MATCH" and set(f) == {"CE-2"}
    assert (f["CE-2"].severity, f["CE-2"].confidence_impact) == ("MEDIUM", -0.10)
    assert "different handles" in f["CE-2"].observation
    assert a.adjusted_confidence == pytest.approx(0.70 - 0.10)


def test_phase_3_associations_now_carry_their_own_findings(seeded):
    db, _ = seeded
    assert set(findings(db, assoc_between(db, 1, 2))) == {"CE-5", "CE-7"}      # CBI vs Customs, Hinglish vs English
    assert set(findings(db, assoc_between(db, 1, 4))) == {"CE-7"}              # same institution, different language mix
    assert assoc_between(db, 1, 4).status == "CANDIDATE_ASSOCIATION"           # LOW findings never dispute


def test_disputed_links_do_not_form_hypotheses(seeded):
    db, _ = seeded
    members = {}
    for c in db.query(Campaign):
        members[c.id] = {m.incident_id for m in db.query(CampaignMember).filter(CampaignMember.campaign_id == c.id)}
    assert sorted(members.values(), key=min) == [{1, 2, 4}, {8, 9}]
    assert not ({3, 5, 6, 7} & set().union(*members.values()))


def test_the_risk_ledger_never_counts_a_disputed_link(seeded):
    db, ids = seeded
    for incident_id in (3, 5, 6, 7):
        analysis = db.query(Analysis).filter(Analysis.incident_id == incident_id).order_by(Analysis.id.desc()).first()
        ledger = db.query(RiskContribution).filter(RiskContribution.analysis_id == analysis.id).all()
        assert not [r for r in ledger if r.factor.startswith("F3")], incident_id
        assert sum(r.contribution for r in ledger) == analysis.risk_score        # and the ledger still sums exactly
    assert len(ids) == 9
