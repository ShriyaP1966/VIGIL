import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Association, Incident, Entity, CounterEvidence, Review
from backend.app.schemas.schemas import AssociationInspectorResponse

router = APIRouter()


@router.get("/associations/{assoc_id}", response_model=AssociationInspectorResponse)
def api_get_association_inspector(assoc_id: int, db: Session = Depends(get_db)):
    assoc = db.query(Association).filter(Association.id == assoc_id).first()
    if not assoc:
        raise HTTPException(status_code=404, detail="Association not found")

    inc_a = db.query(Incident).filter(Incident.id == assoc.incident_a_id).first()
    inc_b = db.query(Incident).filter(Incident.id == assoc.incident_b_id).first()

    incidents_payload = [
        {"id": inc_a.id, "title": inc_a.title} if inc_a else {"id": assoc.incident_a_id, "title": "Unknown"},
        {"id": inc_b.id, "title": inc_b.title} if inc_b else {"id": assoc.incident_b_id, "title": "Unknown"},
    ]

    shared_entity_ids = json.loads(assoc.shared_entity_ids_json or "[]")
    shared_entities = []
    for ent_id in shared_entity_ids:
        ent = db.query(Entity).filter(Entity.id == ent_id).first()
        if ent:
            shared_entities.append({
                "entity_id": ent.id,
                "type": ent.type,
                "canonical_value": ent.canonical_value,
                "display_value": ent.display_value,
                "norm_method": ent.norm_method
            })

    evidence_items = json.loads(assoc.supporting_evidence_json or "[]")
    component_scores = json.loads(assoc.component_scores_json or "{}")

    # Fetch counter-evidence
    ce_records = db.query(CounterEvidence).filter(CounterEvidence.association_id == assoc.id).all()
    counter_evidence = [
        {
            "id": ce.id,
            "rule_id": ce.rule_id,
            "kind": ce.kind,
            "severity": ce.severity,
            "observation": ce.observation,
            "evidence_refs": json.loads(ce.evidence_refs_json or "[]"),
            "confidence_impact": ce.confidence_impact,
            "explanation": ce.explanation
        }
        for ce in ce_records
    ]

    # Fetch reviews
    reviews = db.query(Review).filter(Review.target_type == "association", Review.target_id == assoc.id).all()
    review_history = [
        {
            "id": r.id,
            "decision": r.decision,
            "note": r.note,
            "previous_status": r.previous_status,
            "new_status": r.new_status,
            "created_at": r.created_at.isoformat()
        }
        for r in reviews
    ]

    return AssociationInspectorResponse(
        id=assoc.id,
        status=assoc.status,
        match_type=assoc.match_type,
        incidents=incidents_payload,
        similarity=assoc.similarity,
        base_confidence=assoc.base_confidence,
        adjusted_confidence=assoc.adjusted_confidence,
        component_scores=component_scores,
        shared_entities=shared_entities,
        evidence=evidence_items,
        counter_evidence=counter_evidence,
        explanation=assoc.explanation,
        versions={"algorithm": assoc.algorithm_version, "extractor": "regex_gazetteer@3.1.0"},
        review={"state": assoc.status, "history": review_history}
    )
