import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ai_engine.extraction.rule_extractor import get_default_extractor
from backend.app.core.database import get_db
from backend.app.models.models import Association, CounterEvidence, Entity, Incident, Review
from backend.app.schemas.schemas import AssociationInspectorResponse, ReviewRequest
from backend.app.services.association_service import apply_association_review

router = APIRouter()

REVIEW_STATE = {"ACCEPT": "ACCEPTED", "REJECT": "REJECTED", "FLAG": "FLAGGED"}


def build_inspector_payload(db: Session, assoc: Association) -> AssociationInspectorResponse:
    inc_a = db.query(Incident).filter(Incident.id == assoc.incident_a_id).first()
    inc_b = db.query(Incident).filter(Incident.id == assoc.incident_b_id).first()

    incidents_payload = [
        {"id": inc_a.id, "title": inc_a.title} if inc_a else {"id": assoc.incident_a_id, "title": "Unknown"},
        {"id": inc_b.id, "title": inc_b.title} if inc_b else {"id": assoc.incident_b_id, "title": "Unknown"},
    ]

    shared_entities = []
    for ent_id in json.loads(assoc.shared_entity_ids_json or "[]"):
        ent = db.query(Entity).filter(Entity.id == ent_id).first()
        if ent:
            shared_entities.append({
                "entity_id": ent.id, "type": ent.type, "canonical_value": ent.canonical_value,
                "display_value": ent.display_value, "norm_method": ent.norm_method,
            })

    ce_records = db.query(CounterEvidence).filter(CounterEvidence.association_id == assoc.id).all()
    counter_evidence = [
        {
            "id": ce.id, "rule_id": ce.rule_id, "kind": ce.kind, "severity": ce.severity,
            "observation": ce.observation, "evidence_refs": json.loads(ce.evidence_refs_json or "[]"),
            "confidence_impact": ce.confidence_impact, "explanation": ce.explanation,
            "rule_version": ce.rule_version,
        }
        for ce in ce_records
    ]

    reviews = (
        db.query(Review).filter(Review.target_type == "association", Review.target_id == assoc.id)
        .order_by(Review.id).all()
    )
    history = [
        {
            "id": r.id, "decision": r.decision, "note": r.note, "previous_status": r.previous_status,
            "new_status": r.new_status, "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]
    review_state = REVIEW_STATE.get(reviews[-1].decision, "UNREVIEWED") if reviews else "UNREVIEWED"

    dispute: dict = {}
    if assoc.status == "DISPUTED_ASSOCIATION":
        analyst = any(r.new_status == "DISPUTED_ASSOCIATION" for r in reviews)
        dispute = {"source": "ANALYST" if analyst else "RULE",
                   "rules": sorted(c["rule_id"] for c in counter_evidence if c["severity"] == "HIGH")}

    return AssociationInspectorResponse(
        id=assoc.id,
        status=assoc.status,
        match_type=assoc.match_type,
        incidents=incidents_payload,
        similarity=assoc.similarity,
        base_confidence=assoc.base_confidence,
        adjusted_confidence=assoc.adjusted_confidence,
        component_scores=json.loads(assoc.component_scores_json or "{}"),
        shared_entities=shared_entities,
        evidence=json.loads(assoc.supporting_evidence_json or "[]"),
        counter_evidence=counter_evidence,
        explanation=assoc.explanation,
        versions={
            "algorithm": assoc.algorithm_version,
            "extractor": "regex_gazetteer@3.1.0" if assoc.match_type == "EXACT_IDENTIFIER"
            else get_default_extractor().version,
        },
        review={"state": review_state, "history": history},
        dispute=dispute,
    )


@router.get("/associations/{assoc_id}", response_model=AssociationInspectorResponse)
def api_get_association_inspector(assoc_id: int, db: Session = Depends(get_db)):
    assoc = db.query(Association).filter(Association.id == assoc_id).first()
    if not assoc:
        raise HTTPException(status_code=404, detail="Association not found")
    return build_inspector_payload(db, assoc)


@router.post("/associations/{assoc_id}/review", response_model=AssociationInspectorResponse)
def api_review_association(assoc_id: int, data: ReviewRequest, db: Session = Depends(get_db)):
    """Analyst decision. ACCEPT -> ANALYST_VERIFIED_ASSOCIATION, REJECT -> REJECTED_ASSOCIATION,
    FLAG -> DISPUTED_ASSOCIATION. Recorded in `reviews` (invariant I3); counter-evidence stays visible."""
    try:
        assoc = apply_association_review(db, assoc_id, data.decision, data.note)
    except LookupError:
        raise HTTPException(status_code=404, detail="Association not found") from None
    return build_inspector_payload(db, assoc)
