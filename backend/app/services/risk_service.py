import re
from sqlalchemy.orm import Session
from backend.app.models.models import Evidence, Mention, Entity, Association, Analysis
from ai_engine.extraction.entity_extractor import ORG_CLASS_BY_CANONICAL

RISK_VERSION = "risk@3.1.0"

# Phase 1 placeholder cues (blueprint §15 Phase 1: "placeholder risk, simple rule, stores contributions").
# Phase 2 replaces keyword cues with the tactic classifier. Cues use word boundaries so that
# e.g. "fir" does not match "confirm".
URGENCY_RE = re.compile(
    r"\b(immediately|turant|abhi turant|urgent(ly)?|last warning|within \d+ ?(minutes?|mins?|hours?))\b",
    re.IGNORECASE,
)
THREAT_RE = re.compile(
    r"\b(arrest(ed)?|warrant|giraftaar|jail|fir|money laundering)\b",
    re.IGNORECASE,
)
BENIGN_RE = re.compile(
    r"(visit (your )?(nearest )?(bank )?branch|helpline 1930|official (bank )?website|never share)",
    re.IGNORECASE,
)

# Institution classes treated as "claimed authority" for the placeholder F1 authority factor.
# A bank or courier brand merely being mentioned (e.g. a genuine HDFC alert) is not impersonation.
AUTHORITY_CLASSES = {"CENTRAL_AGENCY", "POLICE", "TELECOM"}
AUTHORITY_NAMES = {"Reserve Bank of India", "Indian Customs"}

BAND_ORDER = {"LOW": 0, "ELEVATED": 1, "HIGH": 2, "CRITICAL": 3}


def risk_band_for(score: int) -> str:
    """Risk bands (§5.4): LOW 0-29, ELEVATED 30-59, HIGH 60-79, CRITICAL 80-100."""
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "ELEVATED"
    return "LOW"


def _is_authority(canonical_name: str) -> bool:
    return (
        ORG_CLASS_BY_CANONICAL.get(canonical_name) in AUTHORITY_CLASSES
        or canonical_name in AUTHORITY_NAMES
    )


def _first_evidence_matching(evidence_items: list[Evidence], pattern: re.Pattern) -> Evidence | None:
    for ev in evidence_items:
        if pattern.search(ev.normalised_text or ev.original_text):
            return ev
    return None


def calculate_baseline_risk(db: Session, incident_id: int) -> tuple[int, str, list[dict]]:
    """
    Calculate baseline risk heuristic (0-100) and construct contribution ledger (§6.9).
    Risk is an experimental heuristic, NOT a probability of fraud, and is NOT calibrated.
    Contributions sum exactly to the displayed score.
    """
    evidence_items = (
        db.query(Evidence).filter(Evidence.incident_id == incident_id).order_by(Evidence.id).all()
    )
    if not evidence_items:
        return 0, "LOW", []

    contributions: list[dict] = []

    def add(factor: str, ev_ref: str, value: int, explanation: str) -> None:
        contributions.append({
            "factor": factor,
            "evidence_ref": ev_ref,
            "rule_version": RISK_VERSION,
            "contribution": value,
            "effect": "SUPPORTING" if value > 0 else "MITIGATING",
            "explanation": explanation,
        })

    # First mention (evidence id) of each entity type, plus authority organisations.
    mention_rows = (
        db.query(Mention, Entity)
        .join(Evidence, Mention.evidence_id == Evidence.id)
        .join(Entity, Mention.entity_id == Entity.id)
        .filter(Evidence.incident_id == incident_id)
        .order_by(Mention.id)
        .all()
    )
    first_ev_for_type: dict[str, int] = {}
    authority_ev: int | None = None
    for m, ent in mention_rows:
        first_ev_for_type.setdefault(ent.type, m.evidence_id)
        if ent.type == "ORGANISATION" and authority_ev is None and _is_authority(ent.canonical_value):
            authority_ev = m.evidence_id

    # F1: tactic presence (placeholder cues)
    if "UPI_HANDLE" in first_ev_for_type:
        add("F1 tactic presence (Financial Demand via UPI)",
            f"evidence:{first_ev_for_type['UPI_HANDLE']}", 18,
            "A UPI payment handle appears in the evidence.")
    if authority_ev is not None:
        add("F1 tactic presence (Authority Impersonation)",
            f"evidence:{authority_ev}", 14,
            "Names a law-enforcement, customs, telecom or regulatory body (claimed authority).")
    if "URL" in first_ev_for_type:
        add("F1 tactic presence (Unsolicited URL)",
            f"evidence:{first_ev_for_type['URL']}", 12,
            "A web link appears in the evidence (never fetched by VIGIL).")

    urgency_ev = _first_evidence_matching(evidence_items, URGENCY_RE)
    if urgency_ev:
        add("F1 tactic presence (Urgency)", f"evidence:{urgency_ev.id}", 8,
            "Urgency or deadline wording is present.")

    threat_ev = _first_evidence_matching(evidence_items, THREAT_RE)
    if threat_ev:
        add("F1 tactic presence (Threat & Intimidation)", f"evidence:{threat_ev.id}", 14,
            "Wording about arrest, warrants, FIR or similar legal threats is present.")

    # F3: OBSERVED_MATCH to an incident whose own risk band is >= ELEVATED (+6 each, cap +12).
    observed = (
        db.query(Association)
        .filter(
            (Association.incident_a_id == incident_id) | (Association.incident_b_id == incident_id),
            Association.status == "OBSERVED_MATCH",
        )
        .order_by(Association.id)
        .all()
    )
    qualifying: list[Association] = []
    for assoc in observed:
        other_id = assoc.incident_b_id if assoc.incident_a_id == incident_id else assoc.incident_a_id
        other = (
            db.query(Analysis).filter(Analysis.incident_id == other_id).order_by(Analysis.id.desc()).first()
        )
        if other and BAND_ORDER.get(other.risk_band, 0) >= BAND_ORDER["ELEVATED"]:
            qualifying.append(assoc)
    if qualifying:
        add("F3 OBSERVED_MATCH to a higher-risk incident",
            f"assoc:{qualifying[0].id}", min(12, 6 * len(qualifying)),
            f"Shares an identical normalised identifier with {len(qualifying)} incident(s) "
            "scoring ELEVATED or above. This is an observation, not proof of one campaign.")

    # M1: benign-context cues, only when no payment handle is requested.
    benign_ev = _first_evidence_matching(evidence_items, BENIGN_RE)
    supporting_so_far = sum(c["contribution"] for c in contributions)
    if benign_ev and "UPI_HANDLE" not in first_ev_for_type and supporting_so_far > 0:
        add("M1 benign-context cues", f"evidence:{benign_ev.id}", -min(15, supporting_so_far),
            "Directs the reader to an official channel and requests no payment handle.")

    # Clamp to 0..100 while keeping the ledger exact: record the clamp as its own contribution.
    raw = sum(c["contribution"] for c in contributions)
    if raw > 100:
        add("Cap at 100", "global", 100 - raw, "Score capped at the 100-point maximum.")
    final_score = max(0, min(100, raw))
    return final_score, risk_band_for(final_score), contributions
