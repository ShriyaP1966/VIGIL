import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Incident, Evidence, Mention, Entity, Analysis, RiskContribution, Redaction
from backend.app.schemas.schemas import (
    IncidentCreate, IncidentDetailResponse, IncidentListItem, EvidenceCreate, EvidenceSchema,
    EntityMentionSchema, AnalysisSchema, RiskContributionSchema, RedactionSummary
)
from backend.app.services.incident_service import create_incident, add_evidence_to_incident, run_incident_analysis

router = APIRouter()


@router.post("/incidents", response_model=IncidentDetailResponse)
def api_create_incident(data: IncidentCreate, db: Session = Depends(get_db)):
    incident = create_incident(db, data)
    # Auto-run analysis on creation
    run_incident_analysis(db, incident.id)
    return get_incident_detail_helper(db, incident.id)


@router.post("/incidents/{incident_id}/evidence", response_model=EvidenceSchema)
def api_add_evidence(incident_id: int, data: EvidenceCreate, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    evidence = add_evidence_to_incident(db, incident_id, data)
    # Re-run analysis
    run_incident_analysis(db, incident_id)
    
    mentions = db.query(Mention).filter(Mention.evidence_id == evidence.id).all()
    entities_schemas = []
    for m in mentions:
        ent = db.query(Entity).filter(Entity.id == m.entity_id).first()
        if ent:
            entities_schemas.append(EntityMentionSchema(
                id=ent.id,
                type=ent.type,
                canonical_value=ent.canonical_value,
                display_value=ent.display_value,
                norm_method=ent.norm_method,
                span_start=m.span_start,
                span_end=m.span_end,
                confidence=m.extraction_confidence
            ))
    
    return EvidenceSchema(
        id=evidence.id,
        type=evidence.type,
        original_text=evidence.original_text,
        normalised_text=evidence.normalised_text,
        sha256=evidence.sha256,
        provenance=evidence.provenance,
        timestamp=evidence.timestamp,
        entities=entities_schemas
    )


@router.post("/analyze/{incident_id}", response_model=IncidentDetailResponse)
def api_analyze_incident(incident_id: int, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    run_incident_analysis(db, incident_id)
    return get_incident_detail_helper(db, incident_id)


@router.get("/incidents", response_model=List[IncidentListItem])
def api_list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    incidents = db.query(Incident).order_by(Incident.id.desc()).offset(skip).limit(limit).all()
    results = []
    for inc in incidents:
        analysis = db.query(Analysis).filter(Analysis.incident_id == inc.id).order_by(Analysis.id.desc()).first()
        results.append(IncidentListItem(
            id=inc.id,
            title=inc.title,
            source_channel=inc.source_channel,
            language=inc.language,
            status=inc.status,
            risk_score=analysis.risk_score if analysis else 0,
            risk_band=analysis.risk_band if analysis else "LOW",
            created_at=inc.created_at
        ))
    return results


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def api_get_incident(incident_id: int, db: Session = Depends(get_db)):
    return get_incident_detail_helper(db, incident_id)


def get_incident_detail_helper(db: Session, incident_id: int) -> IncidentDetailResponse:
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    evidence_items = db.query(Evidence).filter(Evidence.incident_id == incident_id).all()
    ev_schemas = []
    for ev in evidence_items:
        mentions = db.query(Mention).filter(Mention.evidence_id == ev.id).all()
        ent_schemas = []
        for m in mentions:
            ent = db.query(Entity).filter(Entity.id == m.entity_id).first()
            if ent:
                ent_schemas.append(EntityMentionSchema(
                    id=ent.id,
                    type=ent.type,
                    canonical_value=ent.canonical_value,
                    display_value=ent.display_value,
                    norm_method=ent.norm_method,
                    span_start=m.span_start,
                    span_end=m.span_end,
                    confidence=m.extraction_confidence
                ))
        ev_schemas.append(EvidenceSchema(
            id=ev.id,
            type=ev.type,
            original_text=ev.original_text,
            normalised_text=ev.normalised_text,
            sha256=ev.sha256,
            provenance=ev.provenance,
            timestamp=ev.timestamp,
            entities=ent_schemas
        ))

    analysis = db.query(Analysis).filter(Analysis.incident_id == incident_id).order_by(Analysis.id.desc()).first()
    analysis_schema = None
    if analysis:
        contributions = db.query(RiskContribution).filter(RiskContribution.analysis_id == analysis.id).all()
        c_schemas = [
            RiskContributionSchema(
                factor=c.factor,
                evidence_ref=c.evidence_ref,
                rule_version=c.rule_version,
                contribution=c.contribution,
                effect=c.effect,
                explanation=c.explanation
            )
            for c in contributions
        ]
        analysis_schema = AnalysisSchema(
            id=analysis.id,
            incident_id=analysis.incident_id,
            extractor=analysis.extractor,
            extractor_version=analysis.extractor_version,
            fallback_used=analysis.fallback_used,
            risk_score=analysis.risk_score,
            risk_band=analysis.risk_band,
            risk_version=analysis.risk_version,
            injection_flags=json.loads(analysis.injection_flags_json or "[]"),
            fingerprint=json.loads(analysis.fingerprint_json or "{}"),
            contributions=c_schemas
        )

    redaction_counts = (
        db.query(Redaction.kind, func.count(Redaction.id))
        .filter(Redaction.incident_id == incident_id)
        .group_by(Redaction.kind)
        .order_by(Redaction.kind)
        .all()
    )

    return IncidentDetailResponse(
        id=inc.id,
        title=inc.title,
        source_channel=inc.source_channel,
        language=inc.language,
        status=inc.status,
        is_synthetic=inc.is_synthetic,
        created_at=inc.created_at,
        evidence_items=ev_schemas,
        analysis=analysis_schema,
        redactions=[RedactionSummary(kind=k, count=c) for k, c in redaction_counts],
    )
