import json

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from ai_engine.extraction.tactics import CANONICAL_STAGES, STAGE_OF_LABEL
from ai_engine.fingerprint.similarity import (
    DEFAULT_T_CANDIDATE, FINGERPRINT_VERSION, Fingerprint, compare, lcs_stages,
)
from backend.app.models.models import (
    Analysis, Association, Entity, Evidence, Mention, Review, TacticEvent, Utterance,
)


LINKABLE_TYPES = {"PHONE", "UPI_HANDLE", "DOMAIN", "EMAIL", "URL"}


def is_exact_identifier_match(a: Entity | None, b: Entity | None) -> bool:
    """Invariant I1 predicate: same identifier type and exactly equal canonical value."""
    return (
        a is not None
        and b is not None
        and a.type in LINKABLE_TYPES
        and a.type == b.type
        and a.canonical_value == b.canonical_value
    )


def find_or_create_observed_matches(db: Session, incident_id: int) -> list[Association]:
    """
    Generate OBSERVED_MATCH associations based strictly on EXACT normalised identifier equality.
    Enforces Safety Invariant I1:
    - An OBSERVED_MATCH can exist ONLY if the normalised identifiers are exactly equal.
    Enforces Safety Invariant I2:
    - No fingerprint, ML or Gemini output can create OBSERVED_MATCH.
    """
    # 1. Fetch all mentions in this incident
    current_mentions = (
        db.query(Mention)
        .join(Evidence, Mention.evidence_id == Evidence.id)
        .filter(Evidence.incident_id == incident_id)
        .all()
    )

    if not current_mentions:
        return []

    created_associations = []

    for mention in current_mentions:
        entity = db.query(Entity).filter(Entity.id == mention.entity_id).first()
        if not entity or entity.type not in LINKABLE_TYPES:
            continue

        # Find mentions of this exact canonical entity in other incidents
        other_mentions = (
            db.query(Mention)
            .join(Evidence, Mention.evidence_id == Evidence.id)
            .filter(
                Mention.entity_id == entity.id,
                Evidence.incident_id != incident_id
            )
            .all()
        )

        for other_mention in other_mentions:
            other_evidence = db.query(Evidence).filter(Evidence.id == other_mention.evidence_id).first()
            if not other_evidence:
                continue

            other_inc_id = other_evidence.incident_id
            # Standardize order: smaller ID first
            inc_a = min(incident_id, other_inc_id)
            inc_b = max(incident_id, other_inc_id)

            # Check if association already exists between inc_a and inc_b
            assoc = (
                db.query(Association)
                .filter(
                    Association.incident_a_id == inc_a,
                    Association.incident_b_id == inc_b
                )
                .first()
            )

            # Evidence excerpts
            curr_ev = db.query(Evidence).filter(Evidence.id == mention.evidence_id).first()
            supporting_excerpt_a = (curr_ev.original_text[:150] + "...") if curr_ev else ""
            supporting_excerpt_b = (other_evidence.original_text[:150] + "...")

            evidence_refs = [
                {
                    "evidence_id": mention.evidence_id,
                    "incident_id": incident_id,
                    "entity_id": entity.id,
                    "entity_type": entity.type,
                    "canonical_value": entity.canonical_value,
                    "display_value": entity.display_value,
                    "excerpt": supporting_excerpt_a
                },
                {
                    "evidence_id": other_mention.evidence_id,
                    "incident_id": other_inc_id,
                    "entity_id": entity.id,
                    "entity_type": entity.type,
                    "canonical_value": entity.canonical_value,
                    "display_value": entity.display_value,
                    "excerpt": supporting_excerpt_b
                }
            ]

            # Invariant I1: an OBSERVED_MATCH requires exactly equal normalised identifiers.
            # Compare the two mentions' entities explicitly instead of trusting the join.
            other_entity = db.query(Entity).filter(Entity.id == other_mention.entity_id).first()
            if not is_exact_identifier_match(entity, other_entity):
                continue

            # Prior confidences per blueprint §6.10:
            # exact UPI 0.75, phone 0.70, URL 0.70, domain 0.65, email 0.65
            base_priors = {
                "UPI_HANDLE": 0.75,
                "PHONE": 0.70,
                "URL": 0.70,
                "DOMAIN": 0.65,
                "EMAIL": 0.65
            }
            prior = base_priors.get(entity.type, 0.70)

            if not assoc:
                assoc = Association(
                    incident_a_id=inc_a,
                    incident_b_id=inc_b,
                    match_type="EXACT_IDENTIFIER",
                    status="OBSERVED_MATCH",
                    shared_entity_ids_json=json.dumps([entity.id]),
                    base_confidence=prior,
                    adjusted_confidence=prior,
                    component_scores_json=json.dumps({"exact_identifier_match": 1.0}),
                    supporting_evidence_json=json.dumps(evidence_refs),
                    explanation=f"Exact normalized {entity.type} '{entity.display_value}' observed in evidence of both incidents.",
                    algorithm_version="vigil@3.1.0"
                )
                db.add(assoc)
                db.commit()
                db.refresh(assoc)
                created_associations.append(assoc)
            else:
                # An earlier behaviour-only candidate for this pair is upgraded when an EXACT identifier
                # turns up: the identifier equality (not the fingerprint) is what makes it an observed match.
                was_candidate = assoc.status == "CANDIDATE_ASSOCIATION" and assoc.match_type == "PLAYBOOK"
                shared_ids = json.loads(assoc.shared_entity_ids_json or "[]")
                if was_candidate:
                    playbook_note = assoc.explanation
                    shared_ids = [entity.id]
                    assoc.shared_entity_ids_json = json.dumps(shared_ids)
                    assoc.status = "OBSERVED_MATCH"
                    assoc.match_type = "COMBINED"
                    assoc.base_confidence = prior
                    assoc.adjusted_confidence = prior
                    assoc.supporting_evidence_json = json.dumps(
                        evidence_refs + json.loads(assoc.supporting_evidence_json or "[]"))
                    assoc.explanation = (
                        f"Exact normalized {entity.type} '{entity.display_value}' observed in evidence of both "
                        f"incidents. Behaviour also matches: {playbook_note}")
                    db.commit()
                    db.refresh(assoc)
                    created_associations.append(assoc)
                elif entity.id not in shared_ids:
                    # Update existing association if this entity is not yet recorded
                    shared_ids.append(entity.id)
                    assoc.shared_entity_ids_json = json.dumps(shared_ids)
                    # +0.05 per extra distinct shared identifier (cap +0.15)
                    extra_boost = min(0.15, (len(shared_ids) - 1) * 0.05)
                    assoc.base_confidence = min(0.95, prior + extra_boost)
                    assoc.adjusted_confidence = assoc.base_confidence

                    existing_ev = json.loads(assoc.supporting_evidence_json or "[]")
                    existing_ev.extend(evidence_refs)
                    assoc.supporting_evidence_json = json.dumps(existing_ev)
                    assoc.explanation += f" Additionally shares exact {entity.type} '{entity.display_value}'."
                    db.commit()
                    db.refresh(assoc)

    return created_associations


# ---------------------------------------------------------------------------------------------
# Safety invariants, enforced at the ORM layer (blueprint §6.5)
#   I1  OBSERVED_MATCH needs exactly-equal identifiers (shared entities) and an identifier match type
#   I2  a behaviour-only (PLAYBOOK) association can never be OBSERVED_MATCH or analyst-set
#   I3  ANALYST_VERIFIED / REJECTED require a recorded analyst review, so the engine cannot set them
#   I5  every association has >= 1 evidence reference and a plain-language explanation
# ---------------------------------------------------------------------------------------------

ANALYST_STATUSES = {"ANALYST_VERIFIED_ASSOCIATION", "REJECTED_ASSOCIATION"}
DECISION_STATUS = {
    "ACCEPT": "ANALYST_VERIFIED_ASSOCIATION",
    "REJECT": "REJECTED_ASSOCIATION",
    "FLAG": "DISPUTED_ASSOCIATION",
}


class InvariantViolation(RuntimeError):
    """Raised when code tries to store an association that breaks a safety invariant."""


def _check_association(target: Association) -> None:
    if target.status == "OBSERVED_MATCH":
        shared = json.loads(target.shared_entity_ids_json or "[]")
        if not shared or target.match_type not in ("EXACT_IDENTIFIER", "COMBINED"):
            raise InvariantViolation("I1/I2: OBSERVED_MATCH requires shared exact identifiers, not behaviour alone")
    if not json.loads(target.supporting_evidence_json or "[]") or not (target.explanation or "").strip():
        raise InvariantViolation("I5: an association needs at least one evidence reference and an explanation")


@event.listens_for(Association, "before_insert")
def _association_before_insert(mapper, connection, target: Association) -> None:
    if target.status in ANALYST_STATUSES:
        raise InvariantViolation("I3: an association cannot be created in an analyst-only status")
    _check_association(target)


@event.listens_for(Association, "before_update")
def _association_before_update(mapper, connection, target: Association) -> None:
    _check_association(target)
    if inspect(target).attrs.status.history.has_changes() and target.status in ANALYST_STATUSES:
        recorded = connection.execute(
            select(Review.id).where(
                Review.target_type == "association", Review.target_id == target.id,
                Review.new_status == target.status,
            ).limit(1)
        ).first()
        if recorded is None:
            raise InvariantViolation("I3: this status needs an analyst review recorded in `reviews`")


# ---------------------------------------------------------------------------------------------
# Behavioural candidates (playbook fingerprint)
# ---------------------------------------------------------------------------------------------

def _latest_fingerprints(db: Session) -> dict[int, Fingerprint]:
    latest: dict[int, Analysis] = {}
    for a in db.query(Analysis).order_by(Analysis.id):
        latest[a.incident_id] = a
    return {iid: Fingerprint.from_json(json.loads(a.fingerprint_json or "{}")) for iid, a in latest.items()}


def _stage_evidence(db: Session, incident_id: int) -> list[dict]:
    """One excerpt per detected stage: the strongest tactic event, with the evidence and span it came from."""
    best: dict[str, tuple[TacticEvent, Utterance]] = {}
    rows = (
        db.query(TacticEvent, Utterance)
        .join(Utterance, TacticEvent.utterance_id == Utterance.id)
        .filter(TacticEvent.incident_id == incident_id)
        .order_by(TacticEvent.id)
        .all()
    )
    for ev, utt in rows:
        stage = STAGE_OF_LABEL.get(ev.label)
        if stage and stage != "CREDENTIAL" and (stage not in best or ev.confidence > best[stage][0].confidence):
            best[stage] = (ev, utt)
    refs = []
    for stage in CANONICAL_STAGES:
        if stage in best:
            ev, utt = best[stage]
            start, end = (int(x) for x in ev.evidence_span.split(":"))
            refs.append({
                "evidence_id": utt.evidence_id, "incident_id": incident_id, "stage": stage, "label": ev.label,
                "utterance_id": utt.id, "span": [start, end], "excerpt": utt.text[start:end],
                "extractor": ev.extractor,
            })
    return refs


def _playbook_explanation(fa: Fingerprint, fb: Fingerprint, result, t_candidate: float) -> str:
    shared = " → ".join(lcs_stages(fa.sequence, fb.sequence))
    return (
        f"Both incidents follow the same {result.lcs}-stage script ({shared}). Behavioural (playbook) similarity "
        f"is {result.playbook_sim:.2f}, at or above the {t_candidate:.2f} candidate threshold. This is a candidate "
        "for investigation, not a confirmed link. Language and channel were not used."
    )


def _strip_playbook_scores(assoc: Association) -> None:
    scores = json.loads(assoc.component_scores_json or "{}")
    assoc.component_scores_json = json.dumps({k: v for k, v in scores.items() if k == "exact_identifier_match"})
    assoc.similarity = None
    if assoc.match_type == "COMBINED":
        assoc.match_type = "EXACT_IDENTIFIER"


def update_playbook_candidates(db: Session, incident_id: int, t_candidate: float = DEFAULT_T_CANDIDATE) -> None:
    """Compare this incident's fingerprint with every other incident's latest fingerprint and keep the
    behaviour-based associations in step. A fingerprint can only ever produce CANDIDATE_ASSOCIATION (I2):
    an existing observed or analyst-set association is never re-statused by this function."""
    fingerprints = _latest_fingerprints(db)
    mine = fingerprints.get(incident_id)
    if mine is None:
        return

    for other_id in sorted(i for i in fingerprints if i != incident_id):
        theirs = fingerprints[other_id]
        a_id, b_id = min(incident_id, other_id), max(incident_id, other_id)
        fa, fb = (mine, theirs) if a_id == incident_id else (theirs, mine)
        result = compare(fa, fb, t_candidate)
        existing = (
            db.query(Association)
            .filter(Association.incident_a_id == a_id, Association.incident_b_id == b_id)
            .first()
        )

        if result.is_candidate:
            scores = result.component_scores()
            if existing is None:
                db.add(Association(
                    incident_a_id=a_id, incident_b_id=b_id, match_type="PLAYBOOK",
                    status="CANDIDATE_ASSOCIATION", shared_entity_ids_json="[]",
                    similarity=result.playbook_sim, base_confidence=result.playbook_sim,
                    adjusted_confidence=result.playbook_sim, component_scores_json=json.dumps(scores),
                    supporting_evidence_json=json.dumps(_stage_evidence(db, a_id) + _stage_evidence(db, b_id)),
                    explanation=_playbook_explanation(fa, fb, result, t_candidate),
                    algorithm_version=FINGERPRINT_VERSION,
                ))
            elif existing.status == "CANDIDATE_ASSOCIATION" and existing.match_type == "PLAYBOOK":
                existing.similarity = existing.base_confidence = existing.adjusted_confidence = result.playbook_sim
                existing.component_scores_json = json.dumps(scores)
                existing.supporting_evidence_json = json.dumps(_stage_evidence(db, a_id) + _stage_evidence(db, b_id))
                existing.explanation = _playbook_explanation(fa, fb, result, t_candidate)
            elif existing.status == "OBSERVED_MATCH":
                # Exact identifiers already link this pair; record that the behaviour matches too.
                merged = {**json.loads(existing.component_scores_json or "{}"), **scores}
                existing.component_scores_json = json.dumps(merged)
                existing.similarity = result.playbook_sim
                existing.match_type = "COMBINED"
        elif existing is not None:
            if existing.status == "CANDIDATE_ASSOCIATION" and existing.match_type == "PLAYBOOK":
                db.delete(existing)            # nothing supports it any more and no analyst touched it
            elif existing.status == "OBSERVED_MATCH" and existing.match_type == "COMBINED":
                _strip_playbook_scores(existing)
    db.commit()


# ---------------------------------------------------------------------------------------------
# Analyst review (the ONLY path that sets analyst statuses, I3)
# ---------------------------------------------------------------------------------------------

def apply_association_review(db: Session, assoc_id: int, decision: str, note: str | None) -> Association:
    if decision not in DECISION_STATUS:
        raise ValueError(f"unknown decision {decision!r}")
    assoc = db.query(Association).filter(Association.id == assoc_id).first()
    if assoc is None:
        raise LookupError("Association not found")
    new_status = DECISION_STATUS[decision]
    db.add(Review(
        target_type="association", target_id=assoc.id, decision=decision, note=note,
        previous_status=assoc.status, new_status=new_status,
    ))
    db.flush()                       # the review row exists before the status changes (I3)
    assoc.status = new_status
    db.commit()
    db.refresh(assoc)
    return assoc
