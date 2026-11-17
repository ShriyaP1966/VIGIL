"""Campaign hypotheses (blueprint §6.8, invariant I4): building, review, stability, wording."""
import json
import re
from pathlib import Path

import pytest

from backend.app.models.models import Association, Campaign, CampaignMember, Review
from backend.app.schemas.schemas import EvidenceCreate, IncidentCreate
from backend.app.services.association_service import apply_association_review
from backend.app.services.campaign_service import apply_campaign_review, rebuild_campaigns
from backend.app.services.incident_service import create_incident, run_incident_analysis

ROOT = Path(__file__).resolve().parents[2]

A = ("Caller: This is Inspector Rao from the Cyber Crime Cell. Your Aadhaar is linked to a money laundering case.\n"
     "Caller: You will be arrested within 30 minutes. Do not tell anyone and stay on the video call.\n"
     "Caller: Transfer the security deposit to pay1@okaxis.")
B = ("Caller: I am Officer Sharma from the CBI. A parcel in your name was found with drugs.\n"
     "Caller: A warrant has been issued and you will be arrested. Do not tell your family.\n"
     "Caller: You must act immediately. Pay Rs 50000 to pay1@okaxis.")             # same UPI as A
C = ("Caller: I am Inspector Meera from the Cyber Crime Cell. Your SIM card is linked to a money laundering case.\n"
     "Caller: You will be arrested within 20 minutes. Do not tell anyone and stay on the video call.\n"
     "Caller: Transfer the security deposit to fresh7@ybl.")                      # rotated identifier
LEGIT = ("Caller: This is the local police station calling about your passport verification. "
         "Please visit the station with original documents. No payment is required.")


@pytest.fixture
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def make(db, text):
    inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(text=text)]))
    run_incident_analysis(db, inc.id)
    return inc


def campaigns(db):
    return db.query(Campaign).order_by(Campaign.id).all()


def basis(db, campaign):
    return {m.incident_id: m.membership_basis for m in db.query(CampaignMember).filter(CampaignMember.campaign_id == campaign.id)}


def test_observed_pair_forms_one_unreviewed_hypothesis(db):
    a, b = make(db, A), make(db, B)
    (c,) = campaigns(db)
    assert c.status == "HYPOTHESIS_UNREVIEWED" and c.hypothesis_title.startswith("Campaign hypothesis")
    assert basis(db, c) == {a.id: "OBSERVED", b.id: "OBSERVED"}
    (assoc,) = db.query(Association).all()
    assert c.weakest_link_association_id == assoc.id and c.confidence == pytest.approx(assoc.adjusted_confidence)


def test_candidate_extension_is_marked_weaker_and_confidence_is_the_mean_of_links(db):
    a, b, c3 = make(db, A), make(db, B), make(db, C)
    (camp,) = campaigns(db)
    assert basis(db, camp) == {a.id: "OBSERVED", b.id: "OBSERVED", c3.id: "CANDIDATE"}
    edges = db.query(Association).all()
    assert len(edges) == 3
    assert camp.confidence == pytest.approx(sum(e.adjusted_confidence for e in edges) / 3)
    weakest = min(edges, key=lambda e: (e.adjusted_confidence, e.id))
    assert camp.weakest_link_association_id == weakest.id


def test_behaviour_only_group_is_a_hypothesis_with_candidate_members(db):
    a, c3 = make(db, A), make(db, C)
    (camp,) = campaigns(db)
    assert basis(db, camp) == {a.id: "CANDIDATE", c3.id: "CANDIDATE"}


def test_unrelated_and_legitimate_incidents_form_no_hypothesis(db):
    make(db, A)
    make(db, LEGIT)
    make(db, "Hi beta, are you coming home for dinner?")
    assert campaigns(db) == []


def test_rejected_or_flagged_links_do_not_connect_incidents(db):
    make(db, A), make(db, B)
    (assoc,) = db.query(Association).all()
    apply_association_review(db, assoc.id, "REJECT", None)
    assert campaigns(db) == []                       # the only link is gone and nobody had reviewed the hypothesis


def test_excluded_links_stay_visible_on_a_hypothesis_that_survives(db, client):
    make(db, A), make(db, B), make(db, C)
    link_ac = next(a for a in db.query(Association) if a.match_type == "PLAYBOOK")
    apply_association_review(db, link_ac.id, "FLAG", "contradiction")
    (camp,) = campaigns(db)                           # still connected through the other links
    from backend.app.api.v1.campaigns import _detail
    detail = _detail(db, camp)
    assert [x.id for x in detail.excluded_links] == [link_ac.id]
    assert link_ac.id not in [x.id for x in detail.links]
    assert detail.excluded_links[0].status == "DISPUTED_ASSOCIATION"


@pytest.mark.parametrize("decision,status,label", [
    ("ACCEPT", "ACCEPTED_BY_ANALYST", "Hypothesis accepted by an analyst"),
    ("REJECT", "REJECTED_BY_ANALYST", "Hypothesis rejected by an analyst"),
    ("FLAG", "FLAGGED", "Hypothesis flagged for review"),
])
def test_campaign_review_sets_status_and_writes_audit_row(db, decision, status, label):
    make(db, A), make(db, B)
    (camp,) = campaigns(db)
    apply_campaign_review(db, camp.id, decision, "note")
    db.refresh(camp)
    assert camp.status == status
    review = db.query(Review).filter(Review.target_type == "campaign").one()
    assert (review.target_id, review.decision, review.previous_status, review.new_status) == (
        camp.id, decision, "HYPOTHESIS_UNREVIEWED", status)
    from backend.app.services.campaign_service import STATUS_LABEL
    assert STATUS_LABEL[status] == label and "ypothesis" in label


def test_rebuild_is_idempotent_and_keeps_reviewed_hypotheses_stable(db):
    make(db, A), make(db, B)
    (camp,) = campaigns(db)
    apply_campaign_review(db, camp.id, "ACCEPT", None)
    first = [(c.id, c.status, sorted(basis(db, c).items())) for c in campaigns(db)]
    rebuild_campaigns(db)
    rebuild_campaigns(db)
    assert [(c.id, c.status, sorted(basis(db, c).items())) for c in campaigns(db)] == first
    # A new related incident joins the SAME hypothesis; the analyst's decision is kept.
    c3 = make(db, C)
    (same,) = campaigns(db)
    assert same.id == camp.id and same.status == "ACCEPTED_BY_ANALYST" and c3.id in basis(db, same)


def test_reviewed_hypothesis_is_kept_as_history_when_its_links_disappear(db):
    make(db, A), make(db, B)
    (camp,) = campaigns(db)
    apply_campaign_review(db, camp.id, "ACCEPT", None)
    (assoc,) = db.query(Association).all()
    apply_association_review(db, assoc.id, "REJECT", None)
    assert [c.id for c in campaigns(db)] == [camp.id]         # unreviewed ones vanish; reviewed ones stay


# ---------------------------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------------------------

def _create(client, text):
    r = client.post("/api/v1/incidents", json={"title": "t", "source_channel": "call", "language": "en",
                                               "evidence": [{"type": "transcript", "text": text}]})
    assert r.status_code == 200
    return r.json()["id"]


def test_campaign_endpoints_list_detail_and_review(client):
    a, b, c = _create(client, A), _create(client, B), _create(client, C)
    listing = client.get("/api/v1/campaigns").json()
    assert len(listing) == 1
    item = listing[0]
    assert item["status"] == "HYPOTHESIS_UNREVIEWED" and "ypothesis" in item["status_label"]
    assert item["member_count"] == 3 and item["basis_counts"] == {"OBSERVED": 2, "CANDIDATE": 1}
    assert item["incident_ids"] == [a, b, c]

    detail = client.get(f"/api/v1/campaigns/{item['id']}").json()
    assert [m["membership_basis"] for m in detail["members"]] == ["OBSERVED", "OBSERVED", "CANDIDATE"]
    assert all(m["stage_sequence"] for m in detail["members"])
    assert len(detail["links"]) == 3 and sum(x["is_weakest"] for x in detail["links"]) == 1
    assert detail["weakest_link_association_id"] in [x["id"] for x in detail["links"]]
    assert detail["shared_indicators"] and detail["shared_indicators"][0]["incident_ids"] == [a, b]
    assert detail["shared_indicators"][0]["display_value"] == "pa•••@okaxis"          # masked
    assert "not a confirmed finding" in detail["disclaimer"]
    assert detail["review"] == {"state": "UNREVIEWED", "history": []}

    r = client.post(f"/api/v1/campaigns/{item['id']}/review", json={"decision": "ACCEPT", "note": "ok"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ACCEPTED_BY_ANALYST" and body["status_label"] == "Hypothesis accepted by an analyst"
    assert body["review"]["state"] == "ACCEPTED" and len(body["review"]["history"]) == 1


def test_campaign_endpoint_errors(client):
    assert client.get("/api/v1/campaigns").json() == []
    r = client.get("/api/v1/campaigns/99")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    assert client.post("/api/v1/campaigns/99/review", json={"decision": "ACCEPT"}).status_code == 404
    assert client.post("/api/v1/campaigns/99/review", json={"decision": "CONFIRM"}).status_code == 422


def test_i4_campaigns_are_only_ever_called_hypotheses_in_api_output(client):
    for text in (A, B, C):
        _create(client, text)
    cid = client.get("/api/v1/campaigns").json()[0]["id"]
    texts = [client.get("/api/v1/campaigns").text, client.get(f"/api/v1/campaigns/{cid}").text,
             client.post(f"/api/v1/campaigns/{cid}/review", json={"decision": "ACCEPT"}).text]
    for text in texts:
        assert not re.search(r"confirmed campaign|criminal|guilty|proven", text, re.I), text[:200]
    for status_label in (json.loads(t) for t in texts[:1]):
        assert all("ypothesis" in c["status_label"] for c in status_label)


def test_i4_no_source_file_uses_forbidden_wording():
    forbidden = re.compile(r"confirmed campaign|criminal syndicate|guilty|real-time call protection|live protection", re.I)
    offenders = []
    for folder in ("backend/app", "ai_engine", "frontend/src"):
        for path in (ROOT / folder).rglob("*"):
            if path.suffix in {".py", ".ts", ".tsx"} and "test" not in path.name and "__pycache__" not in str(path):
                for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if forbidden.search(line):
                        offenders.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:90]}")
    assert offenders == [], "\n".join(offenders)
