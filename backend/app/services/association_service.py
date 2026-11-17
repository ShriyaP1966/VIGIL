import json
from sqlalchemy.orm import Session
from backend.app.models.models import (
    Association, Entity, Mention, Evidence
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
                # Update existing association if this entity is not yet recorded
                shared_ids = json.loads(assoc.shared_entity_ids_json or "[]")
                if entity.id not in shared_ids:
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
