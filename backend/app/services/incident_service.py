import json
from dataclasses import dataclass, replace
from sqlalchemy.orm import Session
from backend.app.core.errors import VigilException
from backend.app.models.models import (
    Incident, Evidence, Utterance, Entity, Mention, Analysis, RiskContribution, Association, Redaction
)
from backend.app.schemas.schemas import IncidentCreate, EvidenceCreate
from ai_engine.privacy.redaction import REDACTOR_VERSION, RedactionEvent, redact_evidence, redact_text
from ai_engine.extraction.normalisation import normalise_text, compute_sha256, detect_language, mask_identifier
from ai_engine.extraction.entity_extractor import extract_entities
from backend.app.services.association_service import find_or_create_observed_matches
from backend.app.services.risk_service import calculate_baseline_risk


def _sanitise_failed() -> VigilException:
    return VigilException(
        "The submission could not be sanitised, so nothing was stored.",
        code="REDACTION_FAILED", status_code=500,
    )


@dataclass
class _PreparedEvidence:
    text: str
    speaker_turns: list[dict] | None
    provenance: str
    events: list[RedactionEvent]


def _prepare_evidence(data: EvidenceCreate) -> _PreparedEvidence:
    """Service-layer backup for the schema validator (§5.5): redact again (idempotent) before any row is
    created, so callers that bypass validation (e.g. model_construct) still never store a secret.
    Fails closed: on any error nothing is stored."""
    try:
        safe = redact_evidence(data.text, data.speaker_turns, data.provenance or "user_paste")
    except Exception:
        raise _sanitise_failed() from None
    try:
        earlier = list(data._redactions)  # events the schema validator already recorded
    except AttributeError:
        earlier = []
    return _PreparedEvidence(safe.text, safe.speaker_turns, safe.provenance or "user_paste",
                             earlier + list(safe.events))


def _store_redactions(db: Session, incident_id: int, evidence_id: int | None, events: list[RedactionEvent]) -> None:
    for ev in events:
        db.add(Redaction(
            incident_id=incident_id, evidence_id=evidence_id, field=ev.field, kind=ev.kind,
            span_start=ev.span_start, span_end=ev.span_end, detector_version=REDACTOR_VERSION,
        ))
    if events:
        db.commit()


def create_incident(db: Session, data: IncidentCreate) -> Incident:
    # Sanitise EVERYTHING before the first row is created, so a failure leaves nothing behind.
    try:
        title = redact_text(data.title)
    except Exception:
        raise _sanitise_failed() from None
    try:
        earlier = list(data._redactions)  # events the schema validator already recorded (title/notes)
    except AttributeError:
        earlier = []
    prepared = [_prepare_evidence(ev) for ev in (data.evidence or [])]

    incident = Incident(
        title=title.text,
        source_channel=data.source_channel,
        language=data.language,
        status="open",
        scenario_id=data.scenario_id,
        is_synthetic=True
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    _store_redactions(db, incident.id, None, earlier + [replace(e, field="title") for e in title.events])
    for ev_data, prep in zip(data.evidence or [], prepared):
        add_evidence_to_incident(db, incident.id, ev_data, _prepared=prep)

    return incident


def add_evidence_to_incident(
    db: Session, incident_id: int, data: EvidenceCreate, _prepared: _PreparedEvidence | None = None
) -> Evidence:
    prep = _prepared or _prepare_evidence(data)
    norm_text = normalise_text(prep.text)
    # The stored "original" is the text AFTER redaction, and the hash covers that text: hashing a raw
    # text containing a 4-6 digit OTP would let anyone recover it by brute force (§5.5 over §6.1).
    sha = compute_sha256(prep.text)
    lang = detect_language(prep.text)

    evidence = Evidence(
        incident_id=incident_id,
        type=data.type,
        original_text=prep.text,
        normalised_text=norm_text,
        sha256=sha,
        provenance=prep.provenance,
        timestamp=data.timestamp or None
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    _store_redactions(db, incident_id, evidence.id, prep.events)

    # If speaker turns provided, create utterances
    if prep.speaker_turns:
        for idx, turn in enumerate(prep.speaker_turns):
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
            text=prep.text,
            language=lang
        )
        db.add(utt)
        db.commit()

    # Extract entities from the NORMALISED text (NFKC, zero-width stripped) so that invisible
    # characters cannot split an identifier. Mention spans refer to `normalised_text`.
    raw_entities = extract_entities(norm_text)
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


def run_incident_analysis(db: Session, incident_id: int, _propagate: bool = True) -> Analysis:
    """
    Run full end-to-end analysis on an incident:
    1. Form OBSERVED_MATCH associations from exactly shared normalised identifiers
    2. Calculate risk heuristic & contribution breakdown
    3. Persist Analysis and RiskContribution records
    4. Re-analyse incidents on the other end of an observed match once, so that both ledgers
       reflect the link (F3). Each run is stored as a new Analysis row; the latest one is shown.
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

    if _propagate:
        linked = db.query(Association).filter(
            (Association.incident_a_id == incident_id) | (Association.incident_b_id == incident_id),
            Association.status == "OBSERVED_MATCH",
        ).all()
        counterparts = {
            a.incident_b_id if a.incident_a_id == incident_id else a.incident_a_id for a in linked
        }
        for other_id in sorted(counterparts):
            run_incident_analysis(db, other_id, _propagate=False)

    return analysis
