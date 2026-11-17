"""Association service: five states, behavioural candidates, invariants I1/I2/I3/I5, analyst review."""
import json

import pytest

from backend.app.models.models import Association, Review
from backend.app.schemas.schemas import EvidenceCreate, IncidentCreate
from backend.app.services.association_service import (
    InvariantViolation, apply_association_review, update_playbook_candidates,
)
from backend.app.services.incident_service import add_evidence_to_incident, create_incident, run_incident_analysis

# Two full six-stage scripts with different wording, different institutions and different identifiers.
SCRIPT_A = ("Caller: This is Inspector Rao from the Cyber Crime Cell. Your Aadhaar is linked to a money laundering case.\n"
            "Caller: You will be arrested within 30 minutes. Do not tell anyone and stay on the video call.\n"
            "Caller: Transfer the security deposit to pay1@okaxis.")
SCRIPT_B = ("Caller: I am Officer Sharma from the CBI. A parcel in your name was found with drugs.\n"
            "Caller: A warrant has been issued and you will be arrested. Do not tell your family.\n"
            "Caller: You must act immediately. Pay Rs 50000 to refund9@oksbi.")
LEGIT_POLICE = ("Caller: This is the local police station calling about your passport verification. "
                "Please visit the station with original documents. No payment is required.")
FAMILY = "Hi beta, are you coming home for dinner?"


@pytest.fixture
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def make(db, text, title="t", channel="call"):
    inc = create_incident(db, IncidentCreate(title=title, source_channel=channel, evidence=[EvidenceCreate(text=text)]))
    run_incident_analysis(db, inc.id)
    return inc


def associations(db):
    return db.query(Association).order_by(Association.id).all()


# ---------------------------------------------------------------------------------------------
# Behavioural candidates
# ---------------------------------------------------------------------------------------------

def test_rotated_identifiers_still_yield_a_candidate_with_scores_and_evidence(db):
    a, b = make(db, SCRIPT_A), make(db, SCRIPT_B)
    (assoc,) = associations(db)
    assert assoc.status == "CANDIDATE_ASSOCIATION" and assoc.match_type == "PLAYBOOK"
    assert (assoc.incident_a_id, assoc.incident_b_id) == (a.id, b.id)
    assert json.loads(assoc.shared_entity_ids_json) == []             # no shared identifier: behaviour only
    scores = json.loads(assoc.component_scores_json)
    assert {"seq_sim", "inst_match", "pay_match", "order_ok", "playbook_sim"} <= set(scores)
    assert scores["playbook_sim"] == pytest.approx(assoc.similarity) and assoc.similarity >= 0.75
    # I5: evidence references (one excerpt per stage per incident) and a plain-language explanation
    refs = json.loads(assoc.supporting_evidence_json)
    assert {r["incident_id"] for r in refs} == {a.id, b.id}
    assert all(r["excerpt"] and r["stage"] for r in refs)
    assert "not a confirmed link" in assoc.explanation and "AUTHORITY" in assoc.explanation


def test_no_candidate_for_legitimate_or_fragment_incidents(db):
    full = make(db, SCRIPT_A)
    make(db, LEGIT_POLICE)
    make(db, FAMILY)
    make(db, "Caller: This is Inspector Rao from the Cyber Crime Cell. You will be arrested.")  # only 2 stages
    assert associations(db) == []
    assert full.id


def test_cut_off_call_links_through_containment(db):
    make(db, SCRIPT_A)
    # Same institution as SCRIPT_A, cut off after isolation: 4 of 6 stages, no payment request yet.
    cut = make(db, "Caller: This is Inspector Rao from the Cyber Crime Cell. Your Aadhaar is linked to a money laundering case.\n"
                   "Caller: You will be arrested. Do not tell anyone.")
    (assoc,) = associations(db)
    assert assoc.status == "CANDIDATE_ASSOCIATION"
    scores = json.loads(assoc.component_scores_json)
    assert scores["containment_adj"] == 1.0 and scores["lcs"] == 4.0 and scores["lcs_sim"] == pytest.approx(4 / 6)
    assert cut.id in (assoc.incident_a_id, assoc.incident_b_id)


def test_a_cut_off_call_from_a_different_institution_is_not_enough_on_its_own(db):
    # Honest behaviour of the formula: containment helps, but a different institution and no payment
    # request pull the similarity below the 0.75 threshold (0.68), so no candidate is created.
    make(db, SCRIPT_A)
    make(db, "Caller: I am Officer Sharma from the CBI. A parcel in your name was found with drugs.\n"
             "Caller: A warrant has been issued and you will be arrested. Do not tell your family.")
    assert associations(db) == []


def test_shared_identifier_and_matching_script_is_one_observed_association(db):
    text_b = SCRIPT_B.replace("refund9@oksbi", "pay1@okaxis")           # same UPI as SCRIPT_A
    make(db, SCRIPT_A)
    make(db, text_b)
    (assoc,) = associations(db)                                          # one row, not two
    assert assoc.status == "OBSERVED_MATCH" and assoc.match_type == "COMBINED"
    scores = json.loads(assoc.component_scores_json)
    assert scores["exact_identifier_match"] == 1.0 and scores["playbook_sim"] >= 0.75
    assert len(json.loads(assoc.shared_entity_ids_json)) == 1


def test_candidate_is_upgraded_when_an_exact_identifier_appears_later(db):
    a, b = make(db, SCRIPT_A), make(db, SCRIPT_B)
    assert associations(db)[0].status == "CANDIDATE_ASSOCIATION"
    add_evidence_to_incident(db, b.id, EvidenceCreate(type="payment_request", text="Also pay to pay1@okaxis"))
    run_incident_analysis(db, b.id)
    (assoc,) = associations(db)
    assert assoc.status == "OBSERVED_MATCH" and assoc.match_type == "COMBINED"     # I1: the identifier did it
    assert len(json.loads(assoc.shared_entity_ids_json)) == 1
    assert "Exact normalized UPI_HANDLE" in assoc.explanation and a.id


def test_unsupported_candidate_is_withdrawn_when_the_threshold_rises(db):
    a, _ = make(db, SCRIPT_A), make(db, SCRIPT_B)
    assert len(associations(db)) == 1
    update_playbook_candidates(db, a.id, t_candidate=0.99)
    assert associations(db) == []
    update_playbook_candidates(db, a.id, t_candidate=0.75)
    assert len(associations(db)) == 1


def test_language_and_channel_do_not_prevent_or_penalise_a_candidate(db):
    make(db, SCRIPT_A, channel="call")
    make(db, SCRIPT_B.replace("Officer Sharma", "Officer Sharma"), channel="sms")
    (assoc,) = associations(db)
    assert assoc.status == "CANDIDATE_ASSOCIATION"
    assert set(json.loads(assoc.component_scores_json)) .isdisjoint({"language", "channel"})


# ---------------------------------------------------------------------------------------------
# Invariants are enforced by the data layer, not just by convention
# ---------------------------------------------------------------------------------------------

def _assoc(**kw):
    base = dict(incident_a_id=1, incident_b_id=2, match_type="PLAYBOOK", status="CANDIDATE_ASSOCIATION",
                shared_entity_ids_json="[]", base_confidence=0.8, adjusted_confidence=0.8,
                supporting_evidence_json=json.dumps([{"evidence_id": 1, "incident_id": 1, "excerpt": "x"}]),
                explanation="because")
    base.update(kw)
    return Association(**base)


def test_i2_behaviour_alone_cannot_be_an_observed_match(db):
    db.add(_assoc(status="OBSERVED_MATCH"))
    with pytest.raises(InvariantViolation, match="I1/I2"):
        db.commit()
    db.rollback()


def test_i1_observed_match_needs_shared_identifiers_even_with_an_identifier_match_type(db):
    db.add(_assoc(status="OBSERVED_MATCH", match_type="EXACT_IDENTIFIER", shared_entity_ids_json="[]"))
    with pytest.raises(InvariantViolation, match="I1"):
        db.commit()
    db.rollback()


def test_i3_analyst_statuses_cannot_be_created_directly(db):
    for status in ("ANALYST_VERIFIED_ASSOCIATION", "REJECTED_ASSOCIATION"):
        db.add(_assoc(status=status))
        with pytest.raises(InvariantViolation, match="I3"):
            db.commit()
        db.rollback()


def test_i3_status_cannot_be_flipped_to_analyst_verified_without_a_review(db):
    make(db, SCRIPT_A), make(db, SCRIPT_B)
    assoc = associations(db)[0]
    assoc.status = "ANALYST_VERIFIED_ASSOCIATION"
    with pytest.raises(InvariantViolation, match="I3"):
        db.commit()
    db.rollback()
    assert associations(db)[0].status == "CANDIDATE_ASSOCIATION"


def test_i5_association_needs_evidence_and_explanation(db):
    db.add(_assoc(supporting_evidence_json="[]"))
    with pytest.raises(InvariantViolation, match="I5"):
        db.commit()
    db.rollback()
    db.add(_assoc(explanation="  "))
    with pytest.raises(InvariantViolation, match="I5"):
        db.commit()
    db.rollback()


# ---------------------------------------------------------------------------------------------
# Analyst review (service and API)
# ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("decision,status,state", [
    ("ACCEPT", "ANALYST_VERIFIED_ASSOCIATION", "ACCEPTED"),
    ("REJECT", "REJECTED_ASSOCIATION", "REJECTED"),
    ("FLAG", "DISPUTED_ASSOCIATION", "FLAGGED"),
])
def test_review_decisions_set_status_and_write_an_audit_row(db, decision, status, state):
    make(db, SCRIPT_A), make(db, SCRIPT_B)
    assoc = associations(db)[0]
    apply_association_review(db, assoc.id, decision, "checked the excerpts")
    db.refresh(assoc)
    assert assoc.status == status
    (review,) = db.query(Review).all()
    assert (review.target_type, review.target_id, review.decision) == ("association", assoc.id, decision)
    assert (review.previous_status, review.new_status, review.note) == (
        "CANDIDATE_ASSOCIATION", status, "checked the excerpts")


def test_reviewed_status_survives_reanalysis(db):
    a, _ = make(db, SCRIPT_A), make(db, SCRIPT_B)
    assoc = associations(db)[0]
    apply_association_review(db, assoc.id, "ACCEPT", None)
    run_incident_analysis(db, a.id)
    update_playbook_candidates(db, a.id, t_candidate=0.99)     # even a withdrawn similarity cannot erase a review
    assert associations(db)[0].status == "ANALYST_VERIFIED_ASSOCIATION"


def _two_incidents_via_api(client):
    ids = []
    for text in (SCRIPT_A, SCRIPT_B):
        r = client.post("/api/v1/incidents", json={"title": "t", "source_channel": "call", "language": "en",
                                                   "evidence": [{"type": "transcript", "text": text}]})
        assert r.status_code == 200
        ids.append(r.json()["id"])
    graph = client.get("/api/v1/graph").json()
    return [int(e["id"].split("_")[1]) for e in graph["edges"] if e["id"].startswith("assoc_")], graph


def test_candidate_edge_is_in_the_graph_with_its_similarity(client):
    (assoc_id,), graph = _two_incidents_via_api(client)
    edge = next(e for e in graph["edges"] if e["id"] == f"assoc_{assoc_id}")
    assert edge["status"] == "CANDIDATE_ASSOCIATION" and edge["similarity"] >= 0.75
    assert edge["label"] == f"{int(edge['similarity'] * 100)}%"
    payload = client.get(f"/api/v1/associations/{assoc_id}").json()
    assert payload["match_type"] == "PLAYBOOK" and payload["component_scores"]["seq_sim"] > 0
    assert payload["review"] == {"state": "UNREVIEWED", "history": []}
    assert payload["versions"]["algorithm"].startswith("fingerprint@")


def test_review_endpoint_accept_reject_flag(client):
    (assoc_id,), _ = _two_incidents_via_api(client)
    url = f"/api/v1/associations/{assoc_id}/review"

    r = client.post(url, json={"decision": "ACCEPT", "note": "looks right"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ANALYST_VERIFIED_ASSOCIATION"
    assert body["review"]["state"] == "ACCEPTED" and len(body["review"]["history"]) == 1
    assert body["review"]["history"][0]["previous_status"] == "CANDIDATE_ASSOCIATION"

    r = client.post(url, json={"decision": "REJECT"})
    assert r.json()["status"] == "REJECTED_ASSOCIATION" and len(r.json()["review"]["history"]) == 2
    graph = client.get("/api/v1/graph").json()
    assert not [e for e in graph["edges"] if e["id"].startswith("assoc_")]            # hidden by default
    shown = client.get("/api/v1/graph", params={"include_rejected": "true"}).json()
    assert [e for e in shown["edges"] if e["id"] == f"assoc_{assoc_id}"]

    r = client.post(url, json={"decision": "FLAG", "note": "contradicts the other report"})
    assert r.json()["status"] == "DISPUTED_ASSOCIATION" and r.json()["review"]["state"] == "FLAGGED"


def test_review_endpoint_validation_and_errors(client):
    (assoc_id,), _ = _two_incidents_via_api(client)
    assert client.post(f"/api/v1/associations/{assoc_id}/review", json={"decision": "VERIFY"}).status_code == 422
    assert client.post(f"/api/v1/associations/{assoc_id}/review", json={}).status_code == 422
    missing = client.post("/api/v1/associations/9999/review", json={"decision": "ACCEPT"})
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "NOT_FOUND"


def test_review_notes_are_redacted_before_storage(client, session_factory):
    (assoc_id,), _ = _two_incidents_via_api(client)
    r = client.post(f"/api/v1/associations/{assoc_id}/review", json={"decision": "ACCEPT", "note": "victim said OTP is 482913"})
    assert r.status_code == 200 and "482913" not in r.text
    with session_factory() as db:
        assert "482913" not in db.query(Review).one().note


def test_every_verified_association_has_a_matching_accept_review(client, session_factory):
    (assoc_id,), _ = _two_incidents_via_api(client)
    client.post(f"/api/v1/associations/{assoc_id}/review", json={"decision": "ACCEPT"})
    with session_factory() as db:
        verified = db.query(Association).filter(Association.status == "ANALYST_VERIFIED_ASSOCIATION").all()
        accepts = db.query(Review).filter(Review.decision == "ACCEPT").all()
        assert {a.id for a in verified} == {r.target_id for r in accepts}
