import json
from dataclasses import dataclass, replace
from sqlalchemy.orm import Session
from backend.app.core.errors import VigilException
from backend.app.models.models import (
    Incident, Evidence, Utterance, Entity, Mention, Analysis, RiskContribution, Association, Redaction,
    TacticEvent,
)
from ai_engine.extraction.interface import ExtractionResult, UtteranceInput
from ai_engine.guard.injection import detect_injection, flag_ids, mask_spans
from ai_engine.extraction.rule_extractor import get_default_extractor
from ai_engine.extraction.tactics import stage_sequence_from_labels
from ai_engine.extraction.turns import parse_labelled_turns
from backend.app.schemas.schemas import IncidentCreate, EvidenceCreate
from ai_engine.privacy.redaction import REDACTOR_VERSION, RedactionEvent, redact_evidence, redact_text
from ai_engine.extraction.normalisation import normalise_text, compute_sha256, detect_language, mask_identifier
from ai_engine.extraction.entity_extractor import extract_entities
from backend.app.core.config import settings
from backend.app.services.campaign_service import rebuild_campaigns
from backend.app.services.counter_evidence_service import evaluate_incident_associations
from backend.app.services.association_service import find_or_create_observed_matches, update_playbook_candidates
from backend.app.services.risk_service import RISK_VERSION, calculate_risk


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

    # Speaker turns: provided by the caller, or parsed from a pasted "Speaker: text" transcript
    turns = prep.speaker_turns or parse_labelled_turns(prep.text)
    if turns:
        for idx, turn in enumerate(turns):
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


def _incident_utterances(db: Session, incident_id: int) -> list[Utterance]:
    return (
        db.query(Utterance)
        .join(Evidence, Utterance.evidence_id == Evidence.id)
        .filter(Evidence.incident_id == incident_id)
        .order_by(Evidence.id, Utterance.idx)
        .all()
    )


def _extract_and_store_tactics(db: Session, incident_id: int) -> tuple[ExtractionResult, dict, list[str]]:
    """Run the injection guard and the rule extractor over the incident's utterances and persist
    `tactic_events`. Flagged spans are masked before extraction, so injected text cannot create labels.
    Re-analysis replaces the previous events, so they are never duplicated.
    Returns (extraction result, fingerprint, injection rule ids)."""
    incident = db.query(Incident).filter(Incident.id == incident_id).one()
    rows = _incident_utterances(db, incident_id)
    injection_flags = [detect_injection(u.text) for u in rows]
    inputs = [
        UtteranceInput(idx=i, speaker=u.speaker, text=mask_spans(u.text, flags),
                       t_start_sec=u.t_start_sec, language=u.language)
        for i, (u, flags) in enumerate(zip(rows, injection_flags))
    ]
    extractor = get_default_extractor()
    result = extractor.analyze(inputs)

    db.query(TacticEvent).filter(TacticEvent.incident_id == incident_id).delete()
    for row, ur in zip(rows, result.utterances):
        for label in ur.tactic_labels:
            for start, end in ur.label_spans.get(label, []):
                db.add(TacticEvent(
                    incident_id=incident_id, utterance_id=row.id, label=label,
                    confidence=ur.confidence_scores[label],
                    extractor=result.extractor_version, evidence_span=f"{start}:{end}",
                ))
    db.commit()

    # First-cut fingerprint: stages in order of first appearance. The full temporal engine is Phase 3.
    fingerprint = {
        "stage_sequence": stage_sequence_from_labels([ur.tactic_labels for ur in result.utterances]),
        "credential_requested": any("CREDENTIAL_REQUEST" in ur.tactic_labels for ur in result.utterances),
        "institution_class": result.institution_class,
        "payment_channel": result.payment_channel,
        "language": result.detected_language,
        "channel": incident.source_channel,
    }
    return result, fingerprint, flag_ids([f for flags in injection_flags for f in flags])


def _refresh_risk(db: Session, analysis: Analysis, injection_flagged: bool) -> None:
    """Recompute the risk score and ledger of an existing analysis (same row, same version)."""
    score, band, contributions = calculate_risk(db, analysis.incident_id, injection_flagged=injection_flagged)
    analysis.risk_score, analysis.risk_band = score, band
    # Replace through the relationship (delete-orphan): a bulk delete followed by inserts would reuse SQLite row
    # ids while the old objects are still in the session's identity map.
    analysis.contributions = [
        RiskContribution(
            factor=c["factor"], evidence_ref=c.get("evidence_ref"), rule_version=c["rule_version"],
            contribution=c["contribution"], effect=c["effect"], explanation=c["explanation"],
        )
        for c in contributions
    ]
    db.commit()


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

    # 2. Injection guard + tactic extraction (rules) -> tactic_events + first-cut fingerprint
    extraction, fingerprint, injection_ids = _extract_and_store_tactics(db, incident_id)

    # 3. Calculate risk heuristic from the persisted tactic events. A manipulation attempt can never
    #    lower the score: when flagged, no mitigating factor is applied.
    risk_score, risk_band, contributions = calculate_risk(db, incident_id, injection_flagged=bool(injection_ids))

    # 4. Create Analysis record
    analysis = Analysis(
        incident_id=incident_id,
        extractor=extraction.extractor_name,
        extractor_version=extraction.extractor_version,
        fallback_used=extraction.fallback_used,
        fingerprint_json=json.dumps(fingerprint),
        risk_score=risk_score,
        risk_band=risk_band,
        risk_version=RISK_VERSION,
        injection_flags_json=json.dumps(injection_ids)
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

    # 5. Behavioural candidates: compare this incident's fingerprint with all others (never creates an
    #    observed or analyst-set association, I2)
    update_playbook_candidates(db, incident_id, settings.T_CANDIDATE)

    # 6. Counter-evidence: why these links might NOT hold. A HIGH finding makes a link DISPUTED; if a link
    #    flipped between observed and disputed, the risk ledger (F3) must not count it, so it is recomputed.
    if evaluate_incident_associations(db, incident_id):
        _refresh_risk(db, analysis, injection_flagged=bool(injection_ids))

    if _propagate:
        linked = db.query(Association).filter(
            (Association.incident_a_id == incident_id) | (Association.incident_b_id == incident_id),
            Association.status.in_(("OBSERVED_MATCH", "DISPUTED_ASSOCIATION")),
        ).all()
        counterparts = {
            a.incident_b_id if a.incident_a_id == incident_id else a.incident_a_id for a in linked
        }
        for other_id in sorted(counterparts):
            run_incident_analysis(db, other_id, _propagate=False)
        rebuild_campaigns(db)       # hypotheses follow the associations (once per top-level analysis)

    return analysis
