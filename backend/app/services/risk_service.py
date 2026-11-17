"""Incident risk indicator (blueprint §6.9): an EXPERIMENTAL HEURISTIC, not a probability and not calibrated.

risk = clip( sum(supporting) - sum(mitigating), 0, 100 ). Every factor is returned as a ledger entry with
its evidence reference, rule version, signed contribution, effect and a plain-language explanation, and the
entries always sum exactly to the score. Weights are a-priori priors (not learned) and live in
ai_engine/extraction/tactics.py. Phase 4 moves them to config/risk_weights.json.
"""

from sqlalchemy.orm import Session

from ai_engine.extraction.tactics import ALL_STAGES, CANONICAL_STAGES, STAGE_OF_LABEL, STAGE_WEIGHTS
from backend.app.models.models import Analysis, Association, Evidence, Mention, TacticEvent

RISK_VERSION = "risk@3.1.1"

F1_CAP = 70            # maximum total of the per-stage presence factors
F2_ORDER_BONUS = 10    # >= 3 stages observed in canonical order
F3_PER_LINK, F3_CAP = 6, 12
M1_BENIGN, M2_WEAK, M3_UNCERTAIN = 15, 10, 5
WEAK_CONFIDENCE = 0.8       # "low confidence" for M2: only the weakest rule tier falls below this
UNCERTAIN_ENTITY_CONFIDENCE = 0.7

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


def _longest_canonical_run(first_utterance: dict[str, int]) -> tuple[int, str | None]:
    """Longest strictly increasing run (by canonical stage order) in the order stages first appeared.
    Returns (length, last stage of one longest run)."""
    appeared = sorted((s for s in first_utterance if s in CANONICAL_STAGES),
                      key=lambda s: (first_utterance[s], CANONICAL_STAGES.index(s)))
    pos = [CANONICAL_STAGES.index(s) for s in appeared]
    best, best_end = 0, None
    lengths = [1] * len(pos)
    for i in range(len(pos)):
        for j in range(i):
            if pos[j] < pos[i]:
                lengths[i] = max(lengths[i], lengths[j] + 1)
        if lengths[i] > best:
            best, best_end = lengths[i], appeared[i]
    return best, best_end


def calculate_risk(db: Session, incident_id: int, injection_flagged: bool = False) -> tuple[int, str, list[dict]]:
    """Return (score, band, ledger). If `injection_flagged`, no mitigating factor is applied: a manipulation
    attempt can never lower the score (§6.4 safety floor)."""
    events = db.query(TacticEvent).filter(TacticEvent.incident_id == incident_id).all()

    # Best event per stage (highest confidence, then earliest utterance) and first appearance per stage
    best: dict[str, TacticEvent] = {}
    first_utterance: dict[str, int] = {}
    legitimate_seen = False
    for ev in events:
        if ev.label == "LEGITIMATE":
            legitimate_seen = True
        stage = STAGE_OF_LABEL.get(ev.label)
        if stage is None:
            continue
        if stage not in best or (-ev.confidence, ev.utterance_id) < (-best[stage].confidence, best[stage].utterance_id):
            best[stage] = ev
        first_utterance[stage] = min(first_utterance.get(stage, ev.utterance_id), ev.utterance_id)

    ledger: list[dict] = []

    def add(factor: str, ref: str, value: int, explanation: str) -> None:
        ledger.append({
            "factor": factor, "evidence_ref": ref, "rule_version": RISK_VERSION, "contribution": value,
            "effect": "SUPPORTING" if value > 0 else "MITIGATING", "explanation": explanation,
        })

    def running() -> int:
        return sum(c["contribution"] for c in ledger)

    # F1: tactic presence, once per distinct stage
    for stage in ALL_STAGES:
        if stage in best:
            ev = best[stage]
            add(f"F1 tactic presence: {stage}", f"utterance:{ev.utterance_id}", STAGE_WEIGHTS[stage],
                f"The {stage.lower()} stage was detected ({ev.label}, rule confidence {ev.confidence:.2f}).")
    f1_total = running()
    if f1_total > F1_CAP:
        add("F1 cap", "global", F1_CAP - f1_total,
            f"Tactic-presence factors are capped at +{F1_CAP} in total.")

    # F2: canonical progression
    run_len, run_end = _longest_canonical_run(first_utterance)
    if run_len >= 3:
        add("F2 canonical order observed", f"utterance:{best[run_end].utterance_id}", F2_ORDER_BONUS,
            f"{run_len} stages appear in the typical scam order (authority, allegation, threat, isolation, urgency, demand).")

    # F3: OBSERVED_MATCH to an incident whose own risk band is >= ELEVATED (+6 each, cap +12)
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
        other = db.query(Analysis).filter(Analysis.incident_id == other_id).order_by(Analysis.id.desc()).first()
        if other and BAND_ORDER.get(other.risk_band, 0) >= BAND_ORDER["ELEVATED"]:
            qualifying.append(assoc)
    if qualifying:
        add("F3 OBSERVED_MATCH to a higher-risk incident", f"assoc:{qualifying[0].id}",
            min(F3_CAP, F3_PER_LINK * len(qualifying)),
            f"Shares an identical normalised identifier with {len(qualifying)} incident(s) scoring ELEVATED "
            "or above. This is an observation, not proof of one campaign.")

    # Mitigating factors. Each is limited to what has been added so far, so the score never goes below 0.
    if not injection_flagged and running() > 0:
        has_demand = "DEMAND" in best or "CREDENTIAL" in best
        if legitimate_seen and not has_demand:
            add("M1 benign-context cues", f"utterance:{_first_legit_utterance(events)}",
                -min(M1_BENIGN, running()),
                "Directs the reader to an official channel or gives safety advice, and requests no payment or credentials.")
        if running() > 0 and len(best) == 1 and next(iter(best.values())).confidence < WEAK_CONFIDENCE:
            only = next(iter(best.values()))
            add("M2 weak evidence", f"utterance:{only.utterance_id}", -min(M2_WEAK, running()),
                "Only one stage was detected, and only by a low-confidence rule.")
        if running() > 0 and _has_uncertain_entity(db, incident_id):
            add("M3 uncertain extraction", "global", -min(M3_UNCERTAIN, running()),
                "An extracted identifier has low extraction confidence.")

    raw = running()
    if raw > 100:  # unreachable with the current weights (maximum 92); kept so the ledger stays exact
        add("Cap at 100", "global", 100 - raw, "Score capped at the 100-point maximum.")
    score = max(0, min(100, running()))
    return score, risk_band_for(score), ledger


def _first_legit_utterance(events: list[TacticEvent]) -> int:
    return min(ev.utterance_id for ev in events if ev.label == "LEGITIMATE")


def _has_uncertain_entity(db: Session, incident_id: int) -> bool:
    return (
        db.query(Mention)
        .join(Evidence, Mention.evidence_id == Evidence.id)
        .filter(Evidence.incident_id == incident_id, Mention.extraction_confidence < UNCERTAIN_ENTITY_CONFIDENCE)
        .first()
    ) is not None
