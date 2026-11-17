"""Applies the counter-evidence rules to stored associations (blueprint §6.10).

For every association touching an incident: build the pair context from the database, run the rules, replace the
stored findings, recompute `adjusted_confidence = clip(base + sum of impacts, 0, 1)`, and set the status:
  * any HIGH finding makes a system-created association DISPUTED_ASSOCIATION;
  * an analyst decision (verified, rejected, or a flag) is never overridden, and findings stay stored and
    visible whatever the analyst decides;
  * a system-set DISPUTED reverts when no HIGH finding remains (an analyst's FLAG never reverts).
Campaign hypotheses aggregate the same findings at read time (see the campaigns API).
"""

import json

from sqlalchemy.orm import Session

from ai_engine.counter_evidence.rules import (
    PairContext, PaymentHandle, SharedIdentifier, adjusted_confidence, evaluate_pair, has_high_severity, load_config,
)
from ai_engine.fingerprint.similarity import Fingerprint
from backend.app.models.models import (
    Analysis, Association, CounterEvidence, Entity, Evidence, Mention, Review, TacticEvent,
)
from backend.app.services.association_service import _stage_evidence

SYSTEM_STATUSES = {"OBSERVED_MATCH", "CANDIDATE_ASSOCIATION", "DISPUTED_ASSOCIATION"}


def _latest_analysis(db: Session, incident_id: int) -> Analysis | None:
    return db.query(Analysis).filter(Analysis.incident_id == incident_id).order_by(Analysis.id.desc()).first()


def _is_legitimate(db: Session, incident_id: int, analysis: Analysis | None) -> bool:
    """Labelled legitimate: a benign-cue tactic event and a LOW risk band."""
    has_label = db.query(TacticEvent).filter(
        TacticEvent.incident_id == incident_id, TacticEvent.label == "LEGITIMATE").first() is not None
    return has_label and analysis is not None and analysis.risk_band == "LOW"


def _handles(db: Session, incident_id: int) -> tuple[PaymentHandle, ...]:
    rows = (
        db.query(Mention, Entity, Evidence)
        .join(Entity, Mention.entity_id == Entity.id)
        .join(Evidence, Mention.evidence_id == Evidence.id)
        .filter(Evidence.incident_id == incident_id, Entity.type == "UPI_HANDLE")
        .order_by(Mention.id)
        .all()
    )
    seen, out = set(), []
    for _m, ent, ev in rows:
        if ent.canonical_value not in seen:
            seen.add(ent.canonical_value)
            out.append(PaymentHandle(ent.canonical_value, ent.display_value, ev.id, incident_id))
    return tuple(out)


def _shared_identifiers(db: Session, assoc: Association) -> tuple[SharedIdentifier, ...]:
    refs_all = json.loads(assoc.supporting_evidence_json or "[]")
    out = []
    for ent_id in json.loads(assoc.shared_entity_ids_json or "[]"):
        ent = db.query(Entity).filter(Entity.id == ent_id).first()
        if ent is None:
            continue
        confidences = [
            m.extraction_confidence for m in db.query(Mention).filter(Mention.entity_id == ent_id)
        ] or [1.0]
        refs = tuple(
            {"evidence_id": r["evidence_id"], "incident_id": r["incident_id"], "excerpt": r.get("excerpt", ""),
             "entity": ent.display_value}
            for r in refs_all if r.get("entity_id") == ent_id
        )
        out.append(SharedIdentifier(ent.type, ent.canonical_value, ent.display_value, refs, min(confidences)))
    return tuple(out)


def build_context(db: Session, assoc: Association) -> PairContext | None:
    an_a, an_b = _latest_analysis(db, assoc.incident_a_id), _latest_analysis(db, assoc.incident_b_id)
    if an_a is None or an_b is None:
        return None
    return PairContext(
        incident_a=assoc.incident_a_id, incident_b=assoc.incident_b_id,
        fp_a=Fingerprint.from_json(json.loads(an_a.fingerprint_json or "{}")),
        fp_b=Fingerprint.from_json(json.loads(an_b.fingerprint_json or "{}")),
        shared=_shared_identifiers(db, assoc),
        handles_a=_handles(db, assoc.incident_a_id), handles_b=_handles(db, assoc.incident_b_id),
        legitimate={assoc.incident_a_id: _is_legitimate(db, assoc.incident_a_id, an_a),
                    assoc.incident_b_id: _is_legitimate(db, assoc.incident_b_id, an_b)},
        stage_refs_a=tuple(_stage_evidence(db, assoc.incident_a_id)),
        stage_refs_b=tuple(_stage_evidence(db, assoc.incident_b_id)),
    )


def _analyst_flagged(db: Session, assoc_id: int) -> bool:
    return db.query(Review).filter(
        Review.target_type == "association", Review.target_id == assoc_id,
        Review.new_status == "DISPUTED_ASSOCIATION").first() is not None


def evaluate_association(db: Session, assoc: Association, config: dict | None = None) -> bool:
    """Evaluate one association. Returns True if its status changed."""
    config = config or load_config()
    ctx = build_context(db, assoc)
    if ctx is None:
        return False
    findings = evaluate_pair(ctx, config)

    db.query(CounterEvidence).filter(CounterEvidence.association_id == assoc.id).delete()
    for f in findings:
        db.add(CounterEvidence(
            association_id=assoc.id, rule_id=f.rule_id, kind=f.kind, observation=f.observation,
            evidence_refs_json=json.dumps(f.evidence_refs), severity=f.severity,
            confidence_impact=f.confidence_impact, explanation=f.explanation, rule_version=f.rule_version,
        ))
    assoc.adjusted_confidence = adjusted_confidence(assoc.base_confidence, findings)

    changed = False
    if assoc.status in SYSTEM_STATUSES:
        if has_high_severity(findings) and assoc.status != "DISPUTED_ASSOCIATION":
            assoc.status, changed = "DISPUTED_ASSOCIATION", True
        elif (not has_high_severity(findings) and assoc.status == "DISPUTED_ASSOCIATION"
              and not _analyst_flagged(db, assoc.id)):
            shared = json.loads(assoc.shared_entity_ids_json or "[]")
            assoc.status, changed = ("OBSERVED_MATCH" if shared else "CANDIDATE_ASSOCIATION"), True
    db.commit()
    return changed


def evaluate_incident_associations(db: Session, incident_id: int) -> bool:
    """Evaluate every association touching an incident. Returns True if any status changed."""
    config = load_config()
    changed = False
    for assoc in (db.query(Association)
                  .filter((Association.incident_a_id == incident_id) | (Association.incident_b_id == incident_id))
                  .order_by(Association.id).all()):
        changed = evaluate_association(db, assoc, config) or changed
    return changed
