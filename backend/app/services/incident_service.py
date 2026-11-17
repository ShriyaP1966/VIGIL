import json
from sqlalchemy.orm import Session
from backend.app.models.models import (
    Incident, Evidence, Utterance, Entity, Mention, Analysis, RiskContribution
)
from backend.app.schemas.schemas import IncidentCreate, EvidenceCreate
from ai_engine.extraction.normalisation import normalise_text, compute_sha256, detect_language, mask_identifier
from ai_engine.extraction.entity_extractor import extract_entities
from backend.app.services.association_service import find_or_create_observed_matches
from backend.app.services.risk_service import calculate_baseline_risk


def create_incident(db: Session, data: IncidentCreate) -> Incident:
    incident = Incident(
        title=data.title,
        source_channel=data.source_channel,
        language=data.language,
        status="open",
        scenario_id=data.scenario_id,
        is_synthetic=True
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    if data.evidence:
        for ev_data in data.evidence:
            add_evidence_to_incident(db, incident.id, ev_data)

    return incident


def add_evidence_to_incident(db: Session, incident_id: int, data: EvidenceCreate) -> Evidence:
    norm_text = normalise_text(data.text)
    sha = compute_sha256(data.text)
    lang = detect_language(data.text)

    evidence = Evidence(
        incident_id=incident_id,
        type=data.type,
        original_text=data.text,
        normalised_text=norm_text,
        sha256=sha,
        provenance=data.provenance or "user_paste",
        timestamp=data.timestamp or None
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # If speaker turns provided, create utterances
    if data.speaker_turns:
        for idx, turn in enumerate(data.speaker_turns):
            utt = Utterance(
                evidence_id=evidence.id,
                idx=idx,
                speaker=turn.get("speaker", "unknown"),
                text=turn.get("text", ""),
                t_start_sec=turn.get("t_start_sec"),
                language=turn.get("language", lang)
            )
            db.add(utt)
        db.commit()
    else:
        # Default single utterance
        utt = Utterance(
            evidence_id=evidence.id,
            idx=0,
            speaker="speaker",
            text=data.text,
            language=lang
        )
        db.add(utt)
        db.commit()

    # Extract entities and save mentions
    raw_entities = extract_entities(data.text)
    for ent_data in raw_entities:
        # Check if entity already exists by canonical_value and type
        entity = (
            db.query(Entity)
            .filter(
                Entity.canonical_value == ent_data.canonical_value,
                Entity.type == ent_data.entity_type
            )
            .first()
        )
        if not entity:
            masked = mask_identifier(ent_data.canonical_value, ent_data.entity_type)
            entity = Entity(
                type=ent_data.entity_type,
                canonical_value=ent_data.canonical_value,
                display_value=masked,
                norm_method=ent_data.norm_method
            )
            db.add(entity)
            db.commit()
            db.refresh(entity)

        # Create Mention
        mention = Mention(
            entity_id=entity.id,
            evidence_id=evidence.id,
            span_start=ent_data.span_start,
            span_end=ent_data.span_end,
            extraction_confidence=ent_data.confidence,
            extractor="regex_gazetteer@3.1.0"
        )
        db.add(mention)

    db.commit()
    return evidence


def run_incident_analysis(db: Session, incident_id: int) -> Analysis:
    """
    Run full end-to-end analysis on an incident:
    1. Extract entities & form OBSERVED_MATCH associations
    2. Calculate risk heuristic & contribution breakdown
    3. Persist Analysis and RiskContribution records
    """
    # 1. Generate observed matches
    find_or_create_observed_matches(db, incident_id)

    # 2. Calculate risk heuristic
    risk_score, risk_band, contributions = calculate_baseline_risk(db, incident_id)

    # 3. Create Analysis record
    analysis = Analysis(
        incident_id=incident_id,
        extractor="RuleMLExtractor",
        extractor_version="3.1.0",
        fallback_used=False,
        fingerprint_json=json.dumps({"stage_sequence": []}),
        risk_score=risk_score,
        risk_band=risk_band,
        risk_version="risk@3.1.0",
        injection_flags_json="[]"
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # 4. Save contributions
    for c in contributions:
        rc = RiskContribution(
            analysis_id=analysis.id,
            factor=c["factor"],
            evidence_ref=c.get("evidence_ref"),
            rule_version=c["rule_version"],
            contribution=c["contribution"],
            effect=c["effect"],
            explanation=c["explanation"]
        )
        db.add(rc)

    db.commit()
    return analysis
