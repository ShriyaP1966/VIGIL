import json
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.models import (
    Analysis, Association, Campaign, CounterEvidence, Entity, Evidence, Incident, Mention, Review,
)
from backend.app.schemas.schemas import (
    CampaignDetail, CampaignLink, CampaignListItem, CampaignMemberView, ReviewRequest, SharedIndicator,
)
from backend.app.services.association_service import LINKABLE_TYPES
from backend.app.services.campaign_service import (
    CAMPAIGN_VERSION, CONNECTING, EXCLUDED, STATUS_LABEL, apply_campaign_review,
)

router = APIRouter()

DISCLAIMER = (
    "A campaign hypothesis groups incidents that may be related, based on observed identifiers and similar "
    "behaviour. It is not a confirmed finding and does not attribute activity to any person or organisation. "
    "Analyst review is required before it is relied on."
)
REVIEW_STATE = {"ACCEPT": "ACCEPTED", "REJECT": "REJECTED", "FLAG": "FLAGGED"}


SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _campaign_findings(db: Session, member_ids: set[int]) -> list[dict]:
    """Counter-evidence stored on every link between the members (connecting, disputed or rejected), aggregated at
    read time so it can never go stale and is never hidden by a review. Worst first."""
    rows = []
    for a in db.query(Association).order_by(Association.id).all():
        if a.incident_a_id in member_ids and a.incident_b_id in member_ids:
            for ce in db.query(CounterEvidence).filter(CounterEvidence.association_id == a.id).order_by(CounterEvidence.id):
                rows.append({
                    "association_id": a.id, "incident_a_id": a.incident_a_id, "incident_b_id": a.incident_b_id,
                    "link_status": a.status, "rule_id": ce.rule_id, "kind": ce.kind, "severity": ce.severity,
                    "observation": ce.observation, "explanation": ce.explanation,
                    "confidence_impact": ce.confidence_impact, "rule_version": ce.rule_version,
                    "evidence_refs": json.loads(ce.evidence_refs_json or "[]"),
                })
    return sorted(rows, key=lambda r: (SEVERITY_RANK.get(r["severity"], 9), r["association_id"], r["rule_id"]))


def _list_item(campaign: Campaign, db: Session | None = None) -> CampaignListItem:
    members = sorted(campaign.members, key=lambda m: m.incident_id)
    findings = _campaign_findings(db, {m.incident_id for m in members}) if db is not None else []
    return CampaignListItem(
        counter_evidence_count=len(findings),
        highest_severity=findings[0]["severity"] if findings else None,
        id=campaign.id,
        hypothesis_title=campaign.hypothesis_title,
        status=campaign.status,
        status_label=STATUS_LABEL.get(campaign.status, "Hypothesis"),
        confidence=campaign.confidence,
        member_count=len(members),
        basis_counts=dict(Counter(m.membership_basis for m in members)),
        weakest_link_association_id=campaign.weakest_link_association_id,
        incident_ids=[m.incident_id for m in members],
    )


def _link(a: Association, weakest_id: int | None) -> CampaignLink:
    return CampaignLink(
        id=a.id, incident_a_id=a.incident_a_id, incident_b_id=a.incident_b_id, status=a.status,
        match_type=a.match_type, similarity=a.similarity, adjusted_confidence=a.adjusted_confidence,
        explanation=a.explanation, is_weakest=a.id == weakest_id,
    )


def _detail(db: Session, campaign: Campaign) -> CampaignDetail:
    base = _list_item(campaign, db)
    member_ids = set(base.incident_ids)
    incidents = {i.id: i for i in db.query(Incident).filter(Incident.id.in_(member_ids)).all()}
    analyses: dict[int, Analysis] = {}
    for a in db.query(Analysis).filter(Analysis.incident_id.in_(member_ids)).order_by(Analysis.id):
        analyses[a.incident_id] = a

    members = []
    for m in sorted(campaign.members, key=lambda x: x.incident_id):
        inc, an = incidents.get(m.incident_id), analyses.get(m.incident_id)
        fp = json.loads(an.fingerprint_json or "{}") if an else {}
        members.append(CampaignMemberView(
            incident_id=m.incident_id, title=inc.title if inc else "Unknown",
            source_channel=inc.source_channel if inc else "", language=inc.language if inc else "",
            risk_score=an.risk_score if an else 0, risk_band=an.risk_band if an else "LOW",
            membership_basis=m.membership_basis, stage_sequence=fp.get("stage_sequence", []),
            institution_class=fp.get("institution_class", "UNKNOWN"), payment_channel=fp.get("payment_channel", "UNKNOWN"),
        ))

    inside = [
        a for a in db.query(Association).order_by(Association.id).all()
        if a.incident_a_id in member_ids and a.incident_b_id in member_ids
    ]
    links = [_link(a, campaign.weakest_link_association_id) for a in inside if a.status in CONNECTING]
    excluded = [_link(a, None) for a in inside if a.status in EXCLUDED]

    # Identifiers observed in more than one member (display values are masked)
    seen: dict[int, set[int]] = defaultdict(set)
    rows = (
        db.query(Mention, Evidence).join(Evidence, Mention.evidence_id == Evidence.id)
        .filter(Evidence.incident_id.in_(member_ids)).all()
    )
    for mention, evidence in rows:
        seen[mention.entity_id].add(evidence.incident_id)
    shared = []
    for entity_id, incident_ids in sorted(seen.items()):
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        if entity and entity.type in LINKABLE_TYPES and len(incident_ids) >= 2:
            shared.append(SharedIndicator(type=entity.type, display_value=entity.display_value,
                                          incident_ids=sorted(incident_ids)))

    reviews = (
        db.query(Review).filter(Review.target_type == "campaign", Review.target_id == campaign.id)
        .order_by(Review.id).all()
    )
    history = [{"id": r.id, "decision": r.decision, "note": r.note, "previous_status": r.previous_status,
                "new_status": r.new_status, "created_at": r.created_at.isoformat()} for r in reviews]

    return CampaignDetail(
        **base.model_dump(),
        members=members, links=links, excluded_links=excluded, shared_indicators=shared,
        counter_evidence=(findings := _campaign_findings(db, member_ids)),
        counter_evidence_summary=dict(Counter(f["severity"] for f in findings)),
        review={"state": REVIEW_STATE.get(reviews[-1].decision, "UNREVIEWED") if reviews else "UNREVIEWED",
                "history": history},
        disclaimer=DISCLAIMER, versions={"algorithm": CAMPAIGN_VERSION},
    )


@router.get("/campaigns", response_model=list[CampaignListItem])
def api_list_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).order_by(Campaign.id).all()
    return [_list_item(c, db) for c in campaigns]


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetail)
def api_get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign hypothesis not found")
    return _detail(db, campaign)


@router.post("/campaigns/{campaign_id}/review", response_model=CampaignDetail)
def api_review_campaign(campaign_id: int, data: ReviewRequest, db: Session = Depends(get_db)):
    """Analyst decision on a hypothesis: ACCEPT, REJECT or FLAG. Recorded in `reviews`."""
    try:
        campaign = apply_campaign_review(db, campaign_id, data.decision, data.note)
    except LookupError:
        raise HTTPException(status_code=404, detail="Campaign hypothesis not found") from None
    return _detail(db, campaign)

