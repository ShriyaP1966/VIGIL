"""Counter-evidence end to end (blueprint §6.10): each rule through the real pipeline, the DISPUTED transition,
analyst decisions that are never overridden, and findings that stay visible after an analyst accepts."""
import json

import pytest

from backend.app.models.models import (
    Association, Campaign, CampaignMember, CounterEvidence, Entity, Evidence, Mention, Review,
)
from backend.app.schemas.schemas import EvidenceCreate, IncidentCreate
from backend.app.services.association_service import apply_association_review
from backend.app.services.counter_evidence_service import evaluate_association, evaluate_incident_associations
from backend.app.services.incident_service import add_evidence_to_incident, create_incident, run_incident_analysis
from backend.app.services.seed_service import seed_session


@pytest.fixture
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def make(db, text, channel="call", language="en"):
    inc = create_incident(db, IncidentCreate(title="t", source_channel=channel, language=language,
                                             evidence=[EvidenceCreate(text=text)]))
    run_incident_analysis(db, inc.id)
    return inc


def the_association(db):
    (assoc,) = db.query(Association).all()
    return assoc


def rules(db, assoc):
    return {c.rule_id: c for c in db.query(CounterEvidence).filter(CounterEvidence.association_id == assoc.id)}


FORWARD = ("Caller: This is Inspector Kulkarni from the Cyber Crime Cell.\nCaller: Do not tell anyone and stay on the video call.\n"
           "Caller: Act within 20 minutes.\nCaller: Transfer the security deposit to {upi}.")
REVERSED = ("Caller: Transfer the security deposit to {upi}.\nCaller: Act within 20 minutes.\n"
            "Caller: Do not tell anyone and stay on the video call.\nCaller: This is Inspector Kulkarni from the Cyber Crime Cell.")


# ---------------------------------------------------------------------------------------------
# One positive and one negative per rule, through the pipeline
# ---------------------------------------------------------------------------------------------

def test_ce1_positive_and_negative(db):
    make(db, FORWARD.format(upi="shared1@ybl")), make(db, REVERSED.format(upi="shared1@ybl"))
    a = the_association(db)
    assert "CE-1" in rules(db, a) and a.status == "DISPUTED_ASSOCIATION"


def test_ce1_negative_same_order(db):
    make(db, FORWARD.format(upi="shared1@ybl")), make(db, FORWARD.format(upi="shared1@ybl"))
    a = the_association(db)
    assert "CE-1" not in rules(db, a) and a.status == "OBSERVED_MATCH"


CALLBACK = "Caller: This is Officer Rathod from the Customs Department. Call me back on +91 98765 11111.\nCaller: Transfer the clearance fee to {upi}."


def test_ce2_positive_and_negative(db):
    make(db, CALLBACK.format(upi="alpha11@okaxis")), make(db, CALLBACK.format(upi="beta22@oksbi"))
    a = the_association(db)
    assert "CE-2" in rules(db, a) and a.status == "OBSERVED_MATCH"          # MEDIUM: reduces confidence only


def test_ce2_negative_same_payment_handle(db):
    make(db, CALLBACK.format(upi="alpha11@okaxis")), make(db, CALLBACK.format(upi="alpha11@okaxis"))
    (assoc,) = db.query(Association).all()
    assert "CE-2" not in rules(db, assoc)


def test_ce3_positive_public_helpline_and_negative_ordinary_identifier(db):
    scam = "Caller: This is Mumbai Customs. Pay the clearance fee to {upi}. Verify on helpline 1930."
    make(db, scam.format(upi="one11@oksbi")), make(db, scam.format(upi="two22@okaxis"))
    a = the_association(db)
    assert "CE-3" in rules(db, a) and a.status == "DISPUTED_ASSOCIATION"
    db.query(Association).delete(), db.commit()                           # fresh pair below
    plain = "Caller: This is Mumbai Customs. Pay the clearance fee to shared9@oksbi."
    make(db, plain), make(db, plain)
    ordinary = db.query(Association).filter(Association.status != "DISPUTED_ASSOCIATION").one()
    assert "CE-3" not in rules(db, ordinary)


def test_ce3_positive_identifier_shared_with_a_legitimate_incident(db):
    make(db, "Dear customer, your statement has been dispatched. Never share your OTP. For queries write to refund9@oksbi.")
    make(db, "Caller: This is Mumbai Customs. Pay the clearance fee to refund9@oksbi.")
    a = the_association(db)
    f = rules(db, a)
    assert "CE-3" in f and "labelled legitimate" in f["CE-3"].observation and a.status == "DISPUTED_ASSOCIATION"


def test_ce3_negative_lookalike_domain_is_not_public(db):
    page = "Caller: This is Mumbai Customs. Pay at https://sbi.co.in.evil-pay.example/pay now."
    make(db, page), make(db, page)
    a = the_association(db)
    assert "CE-3" not in rules(db, a) and a.status == "OBSERVED_MATCH"


def test_ce4_positive_only_with_a_low_confidence_extraction_and_negative_otherwise(db):
    text = "Caller: This is Mumbai Customs. Pay the clearance fee to shared9@oksbi."
    make(db, text), make(db, text)
    a = the_association(db)
    assert "CE-4" not in rules(db, a)                                      # real extraction confidence is 0.95
    entity = db.query(Entity).filter(Entity.canonical_value == "shared9@oksbi").one()
    mention = db.query(Mention).filter(Mention.entity_id == entity.id).first()
    mention.extraction_confidence = 0.5
    db.commit()
    evaluate_association(db, a)
    f = rules(db, a)
    assert "CE-4" in f and f["CE-4"].severity == "MEDIUM" and a.status == "OBSERVED_MATCH"


def test_ce5_positive_and_negative(db):
    make(db, "Caller: This is Officer Rao from the CBI. Pay Rs 50000 to shared9@oksbi.")
    make(db, "Caller: This is Officer Rathod from the Customs Department. Pay Rs 50000 to shared9@oksbi.")
    assert "CE-5" in rules(db, the_association(db))
    db.query(Association).delete(), db.commit()
    same = "Caller: This is Officer Rao from the CBI. Pay Rs 50000 to other7@oksbi."
    make(db, same), make(db, same)
    assert all("CE-5" not in rules(db, a) for a in db.query(Association).filter(Association.status != "DISPUTED_ASSOCIATION"))


def test_ce7_positive_and_negative_language(db):
    text = "Caller: This is Officer Rao from the CBI. Pay Rs 50000 to shared9@oksbi."
    hinglish = "Caller: Main CBI officer Rao bol raha hoon. Turant paise bhejo shared9@oksbi par."
    make(db, text), make(db, hinglish)
    a = the_association(db)
    f = rules(db, a)
    assert "CE-7" in f and f["CE-7"].severity == "LOW" and a.status == "OBSERVED_MATCH"
    db.query(Association).delete(), db.commit()
    make(db, text.replace("shared9", "same4")), make(db, text.replace("shared9", "same4"))
    assert all("CE-7" not in rules(db, a) for a in db.query(Association))


# ---------------------------------------------------------------------------------------------
# The DISPUTED transition and its reverse
# ---------------------------------------------------------------------------------------------

def test_a_high_finding_makes_the_link_disputed_and_it_reverts_when_the_cause_disappears(db):
    legit = make(db, "Dear customer, your statement has been dispatched. Never share your OTP. For queries write to refund9@oksbi.")
    make(db, "Caller: This is Mumbai Customs. Pay the clearance fee to refund9@oksbi.")
    a = the_association(db)
    assert a.status == "DISPUTED_ASSOCIATION" and a.adjusted_confidence < a.base_confidence

    # The "legitimate" incident turns out to be a scam: it is no longer labelled legitimate, so CE-3 no longer applies.
    add_evidence_to_incident(db, legit.id, EvidenceCreate(
        text="Caller: This is Inspector Rao from the CBI. You will be arrested within 30 minutes. Transfer the deposit to refund9@oksbi."))
    run_incident_analysis(db, legit.id)
    db.refresh(a)
    assert "CE-3" not in rules(db, a)
    assert a.status == "OBSERVED_MATCH"                                    # system dispute reverted
    assert a.adjusted_confidence == pytest.approx(a.base_confidence + sum(
        c.confidence_impact for c in db.query(CounterEvidence).filter(CounterEvidence.association_id == a.id)))


def test_an_analyst_flag_is_never_reverted_by_the_engine(db):
    make(db, CALLBACK.format(upi="alpha11@okaxis")), make(db, CALLBACK.format(upi="beta22@oksbi"))
    a = the_association(db)
    apply_association_review(db, a.id, "FLAG", "something is off")
    db.refresh(a)
    assert a.status == "DISPUTED_ASSOCIATION"
    evaluate_incident_associations(db, a.incident_a_id)                    # no HIGH finding exists
    db.refresh(a)
    assert a.status == "DISPUTED_ASSOCIATION" and "CE-2" in rules(db, a)


def test_evaluation_is_idempotent_and_never_duplicates_findings(db):
    make(db, FORWARD.format(upi="shared1@ybl")), make(db, REVERSED.format(upi="shared1@ybl"))
    a = the_association(db)
    first = sorted((c.rule_id, c.confidence_impact) for c in db.query(CounterEvidence))
    for _ in range(3):
        evaluate_association(db, a)
        evaluate_incident_associations(db, a.incident_a_id)
    assert sorted((c.rule_id, c.confidence_impact) for c in db.query(CounterEvidence)) == first
    assert db.query(CounterEvidence).count() == len(first)


# ---------------------------------------------------------------------------------------------
# Analyst decisions are never overridden, and findings stay visible after acceptance
# ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("decision,status", [("ACCEPT", "ANALYST_VERIFIED_ASSOCIATION"), ("REJECT", "REJECTED_ASSOCIATION")])
def test_analyst_decision_survives_reevaluation_and_findings_stay_stored(db, decision, status):
    make(db, FORWARD.format(upi="shared1@ybl")), make(db, REVERSED.format(upi="shared1@ybl"))
    a = the_association(db)
    stored = {(c.rule_id, c.confidence_impact) for c in db.query(CounterEvidence)}
    adjusted = a.adjusted_confidence
    apply_association_review(db, a.id, decision, "reviewed")
    for incident_id in (a.incident_a_id, a.incident_b_id):
        run_incident_analysis(db, incident_id)                             # full re-analysis must not touch the decision
    db.refresh(a)
    assert a.status == status
    assert {(c.rule_id, c.confidence_impact) for c in db.query(CounterEvidence)} == stored
    assert a.adjusted_confidence == pytest.approx(adjusted)                # confidence still reflects the findings
    assert db.query(Review).count() == 1


def test_findings_remain_visible_in_the_inspector_after_an_analyst_accepts(client):
    ids = []
    for text in (FORWARD.format(upi="shared1@ybl"), REVERSED.format(upi="shared1@ybl")):
        r = client.post("/api/v1/incidents", json={"title": "t", "source_channel": "call", "language": "en",
                                                   "evidence": [{"type": "transcript", "text": text}]})
        ids.append(r.json()["id"])
    graph = client.get("/api/v1/graph").json()
    assoc_id = int(next(e for e in graph["edges"] if e["id"].startswith("assoc_"))["id"].split("_")[1])

    before = client.get(f"/api/v1/associations/{assoc_id}").json()
    assert before["status"] == "DISPUTED_ASSOCIATION" and before["dispute"] == {"source": "RULE", "rules": ["CE-1"]}
    accepted = client.post(f"/api/v1/associations/{assoc_id}/review", json={"decision": "ACCEPT"}).json()

    assert accepted["status"] == "ANALYST_VERIFIED_ASSOCIATION" and accepted["dispute"] == {}
    assert [c["rule_id"] for c in accepted["counter_evidence"]] == ["CE-1"]           # still there
    assert accepted["counter_evidence"][0]["severity"] == "HIGH" and accepted["counter_evidence"][0]["evidence_refs"]
    assert accepted["adjusted_confidence"] == pytest.approx(before["adjusted_confidence"])
    assert accepted["adjusted_confidence"] < accepted["base_confidence"]


def test_analyst_flag_is_reported_as_an_analyst_dispute(client):
    for text in ("Caller: This is Officer Rathod from the Customs Department. Call me back on +91 98765 11111.\nCaller: Transfer the clearance fee to alpha11@okaxis.",
                 "Caller: This is Officer Rathod from the Customs Department. Call me back on +91 98765 11111.\nCaller: Transfer the clearance fee to beta22@oksbi."):
        client.post("/api/v1/incidents", json={"title": "t", "source_channel": "call", "language": "en",
                                               "evidence": [{"type": "transcript", "text": text}]})
    assoc_id = int(next(e for e in client.get("/api/v1/graph").json()["edges"] if e["id"].startswith("assoc_"))["id"].split("_")[1])
    flagged = client.post(f"/api/v1/associations/{assoc_id}/review", json={"decision": "FLAG"}).json()
    assert flagged["status"] == "DISPUTED_ASSOCIATION" and flagged["dispute"]["source"] == "ANALYST"
    assert [c["rule_id"] for c in flagged["counter_evidence"]] == ["CE-2"]             # the rule finding is still shown


# ---------------------------------------------------------------------------------------------
# Hypotheses aggregate the same findings, and keep them after acceptance
# ---------------------------------------------------------------------------------------------

def test_campaign_aggregates_findings_and_keeps_them_after_an_accepted_dispute(client, session_factory):
    with session_factory() as db:
        seed_session(db)
    campaigns = client.get("/api/v1/campaigns").json()
    assert sorted(c["member_count"] for c in campaigns) == [2, 3]
    by_size = {c["member_count"]: c for c in campaigns}
    assert by_size[2]["counter_evidence_count"] == 1 and by_size[2]["highest_severity"] == "MEDIUM"        # CE-2 only
    assert by_size[3]["highest_severity"] == "MEDIUM"                                                        # CE-5, CE-7 ...
    detail = client.get(f"/api/v1/campaigns/{by_size[3]['id']}").json()
    assert [f["severity"] for f in detail["counter_evidence"]] == sorted(
        (f["severity"] for f in detail["counter_evidence"]), key={"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get)
    assert detail["counter_evidence_summary"] == {"MEDIUM": 1, "LOW": 2}

    # Seeds 3 and 5 are disputed by CE-3 and form no hypothesis. An analyst accepts that link: it now connects the
    # two incidents (analyst basis) and the CE-3 finding stays visible on the new hypothesis.
    graph = client.get("/api/v1/graph").json()
    assoc_35 = next(e for e in graph["edges"] if e["source"] == "incident_3" and e["target"] == "incident_5")
    client.post(f"/api/v1/associations/{assoc_35['id'].split('_')[1]}/review", json={"decision": "ACCEPT"})
    campaigns = client.get("/api/v1/campaigns").json()
    new = next(c for c in campaigns if set(c["incident_ids"]) == {3, 5})
    assert new["basis_counts"] == {"ANALYST": 2} and new["highest_severity"] == "HIGH" and new["counter_evidence_count"] == 2
    detail = client.get(f"/api/v1/campaigns/{new['id']}").json()
    assert detail["counter_evidence"][0]["rule_id"] == "CE-3" and detail["counter_evidence"][0]["severity"] == "HIGH"
    assert detail["status"] == "HYPOTHESIS_UNREVIEWED" and "ypothesis" in detail["status_label"]
    # even after the analyst accepts the hypothesis itself, the findings are still reported
    accepted = client.post(f"/api/v1/campaigns/{new['id']}/review", json={"decision": "ACCEPT"}).json()
    assert accepted["status"] == "ACCEPTED_BY_ANALYST" and accepted["counter_evidence_summary"] == {"HIGH": 1, "MEDIUM": 1}


def test_disputed_link_is_excluded_from_its_hypothesis_but_its_findings_are_still_listed(client, session_factory):
    with session_factory() as db:
        seed_session(db)
        # attach a disputed link to an existing hypothesis: flag the 1-4 candidate; hypothesis {1,2,4} drops member 4
        a14 = db.query(Association).filter(Association.incident_a_id == 1, Association.incident_b_id == 4).one()
        apply_association_review(db, a14.id, "FLAG", None)
        assert db.query(Campaign).count() == 2
        members = {m.incident_id for m in db.query(CampaignMember)}
    assert 4 not in members and {1, 2} <= members
    big = next(c for c in client.get("/api/v1/campaigns").json() if 1 in c["incident_ids"])
    detail = client.get(f"/api/v1/campaigns/{big['id']}").json()
    assert detail["incident_ids"] == [1, 2] and detail["excluded_links"] == []      # member 4 left, so its link is outside
    assert {f["rule_id"] for f in detail["counter_evidence"]} == {"CE-5", "CE-7"}


def test_findings_are_stored_apart_from_the_association_and_unique_per_rule(db):
    seed_session(db)
    keys = [(c.association_id, c.rule_id) for c in db.query(CounterEvidence)]
    assert len(keys) == len(set(keys)) and keys
    for a in db.query(Association):
        high = db.query(CounterEvidence).filter(CounterEvidence.association_id == a.id, CounterEvidence.severity == "HIGH").count()
        assert (a.status == "DISPUTED_ASSOCIATION") == (high > 0)          # no analyst acted: dispute iff a HIGH finding
        assert json.loads(a.supporting_evidence_json) and a.explanation     # the association itself is unchanged (I5)
    assert db.query(Evidence).count() == 9
