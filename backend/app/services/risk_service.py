from sqlalchemy.orm import Session
from backend.app.models.models import (
    Evidence, Mention, Entity, Association
)


def calculate_baseline_risk(db: Session, incident_id: int) -> tuple[int, str, list[dict]]:
    """
    Calculate baseline risk heuristic (0-100) and construct contribution ledger (§6.9).
    Risk is an experimental heuristic, NOT a probability of fraud, and is NOT calibrated.
    Contributions sum exactly to the displayed score.
    """
    evidence_items = db.query(Evidence).filter(Evidence.incident_id == incident_id).all()
    if not evidence_items:
        return 0, "LOW", []

    contributions: list[dict] = []
    total_score = 0

    # 1. Inspect extracted entities
    all_text = " ".join([e.original_text.lower() for e in evidence_items])
    mentions = (
        db.query(Mention)
        .join(Evidence, Mention.evidence_id == Evidence.id)
        .filter(Evidence.incident_id == incident_id)
        .all()
    )
    
    entity_types = set()
    for m in mentions:
        ent = db.query(Entity).filter(Entity.id == m.entity_id).first()
        if ent:
            entity_types.add(ent.type)

    # Factor F1: Suspicious payment / impersonation presence
    if "UPI_HANDLE" in entity_types:
        f_contrib = 18
        contributions.append({
            "factor": "F1 tactic presence (Financial Demand via UPI)",
            "evidence_ref": f"evidence:{evidence_items[0].id}",
            "rule_version": "risk@3.1.0",
            "contribution": f_contrib,
            "effect": "SUPPORTING",
            "explanation": "Direct UPI payment handle identified in communication."
        })
        total_score += f_contrib

    if "ORGANISATION" in entity_types:
        f_contrib = 14
        contributions.append({
            "factor": "F1 tactic presence (Authority Impersonation)",
            "evidence_ref": f"evidence:{evidence_items[0].id}",
            "rule_version": "risk@3.1.0",
            "contribution": f_contrib,
            "effect": "SUPPORTING",
            "explanation": "Claimed representation of law enforcement or regulatory agency."
        })
        total_score += f_contrib

    if "URL" in entity_types:
        f_contrib = 12
        contributions.append({
            "factor": "F1 tactic presence (Phishing / Unsolicited URL)",
            "evidence_ref": f"evidence:{evidence_items[0].id}",
            "rule_version": "risk@3.1.0",
            "contribution": f_contrib,
            "effect": "SUPPORTING",
            "explanation": "External clickable web link provided for payment or credential submission."
        })
        total_score += f_contrib

    # Urgency & Threat keyword heuristics for baseline slice
    urgency_cues = ["immediately", "within 30 minutes", "turant", "urgent", "last warning", "penalty"]
    if any(q in all_text for q in urgency_cues):
        f_contrib = 8
        contributions.append({
            "factor": "F1 tactic presence (Urgency / Coercion)",
            "evidence_ref": f"evidence:{evidence_items[0].id}",
            "rule_version": "risk@3.1.0",
            "contribution": f_contrib,
            "effect": "SUPPORTING",
            "explanation": "Artificial urgency and strict deadlines applied to force compliance."
        })
        total_score += f_contrib

    threat_cues = ["arrest", "warrant", "giraftaar", "jail", "fir", "police", "money laundering"]
    if any(q in all_text for q in threat_cues):
        f_contrib = 14
        contributions.append({
            "factor": "F1 tactic presence (Threat & Intimidation)",
            "evidence_ref": f"evidence:{evidence_items[0].id}",
            "rule_version": "risk@3.1.0",
            "contribution": f_contrib,
            "effect": "SUPPORTING",
            "explanation": "Threats of criminal prosecution, legal arrest, or asset freezing."
        })
        total_score += f_contrib

    # Factor F3: Observed Match to an existing incident
    observed_assocs = (
        db.query(Association)
        .filter(
            ((Association.incident_a_id == incident_id) | (Association.incident_b_id == incident_id)),
            Association.status == "OBSERVED_MATCH"
        )
        .all()
    )
    if observed_assocs:
        f_contrib = min(12, len(observed_assocs) * 6)
        contributions.append({
            "factor": "F3 OBSERVED_MATCH cross-incident link",
            "evidence_ref": f"assoc:{observed_assocs[0].id}",
            "rule_version": "risk@3.1.0",
            "contribution": f_contrib,
            "effect": "SUPPORTING",
            "explanation": f"Shares identical normalized identifier with {len(observed_assocs)} other evidence record(s)."
        })
        total_score += f_contrib

    # Mitigating factors (M1, M2)
    benign_cues = ["visit branch", "helpline 1930", "official bank website", "no fee required"]
    if any(b in all_text for b in benign_cues) and total_score > 0:
        m_contrib = -15
        contributions.append({
            "factor": "M1 benign-context cues",
            "evidence_ref": f"evidence:{evidence_items[0].id}",
            "rule_version": "risk@3.1.0",
            "contribution": m_contrib,
            "effect": "MITIGATING",
            "explanation": "Advises visiting official bank branch or reporting through official channels."
        })
        total_score += m_contrib

    # Final score clamping: 0 to 100
    final_score = max(0, min(100, total_score))

    # Risk band mapping (§5.4): LOW 0-29, ELEVATED 30-59, HIGH 60-79, CRITICAL 80-100
    if final_score >= 80:
        band = "CRITICAL"
    elif final_score >= 60:
        band = "HIGH"
    elif final_score >= 30:
        band = "ELEVATED"
    else:
        band = "LOW"

    return final_score, band, contributions
