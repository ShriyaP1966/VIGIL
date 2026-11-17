"""Stage-based risk indicator and its exact-sum ledger (blueprint §6.9)."""
import pytest

from backend.app.models.models import Entity, Evidence, Mention, RiskContribution, TacticEvent
from backend.app.schemas.schemas import EvidenceCreate, IncidentCreate
from backend.app.services.incident_service import create_incident, run_incident_analysis
from backend.app.services.risk_service import calculate_risk, risk_band_for

FULL = ("Caller: This is Inspector Rao from the Cyber Crime Cell. Your Aadhaar is linked to a money laundering case.\n"
        "Caller: You will be arrested within 30 minutes. Do not tell anyone and stay on the video call.\n"
        "Caller: Transfer the security deposit to our account.")


@pytest.fixture
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def analyse(db, text):
    inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(text=text)]))
    analysis = run_incident_analysis(db, inc.id)
    ledger = db.query(RiskContribution).filter(RiskContribution.analysis_id == analysis.id).all()
    return inc, analysis, ledger


def factor(ledger, prefix):
    return [r for r in ledger if r.factor.startswith(prefix)]


@pytest.mark.parametrize("score,band", [
    (0, "LOW"), (29, "LOW"), (30, "ELEVATED"), (59, "ELEVATED"),
    (60, "HIGH"), (79, "HIGH"), (80, "CRITICAL"), (100, "CRITICAL"),
])
def test_band_boundaries(score, band):
    assert risk_band_for(score) == band


def test_full_playbook_uses_stage_weights_cap_and_order_bonus(db):
    _, analysis, ledger = analyse(db, FULL)
    stages = {r.factor.split(": ")[1]: r.contribution for r in factor(ledger, "F1 tactic presence")}
    assert stages == {"AUTHORITY": 6, "ALLEGATION": 10, "THREAT": 14, "ISOLATION": 16, "URGENCY": 8, "DEMAND": 18}
    assert [r.contribution for r in factor(ledger, "F1 cap")] == [-2]       # 72 raw, capped at 70
    assert [r.contribution for r in factor(ledger, "F2")] == [10]
    assert analysis.risk_score == 80 and analysis.risk_band == "CRITICAL"
    assert sum(r.contribution for r in ledger) == analysis.risk_score


def test_every_entry_has_ref_version_effect_and_explanation(db):
    _, _, ledger = analyse(db, FULL)
    for r in ledger:
        assert r.factor and r.explanation and r.rule_version == "risk@3.1.1"
        assert r.evidence_ref and (r.evidence_ref.startswith("utterance:") or r.evidence_ref == "global")
        assert (r.effect == "SUPPORTING") == (r.contribution > 0)


def test_stage_refs_point_at_the_utterance_that_fired(db):
    inc, _, ledger = analyse(db, "Caller: Hello there.\nCaller: You will be arrested immediately.")
    threat = factor(ledger, "F1 tactic presence: THREAT")[0]
    event = db.query(TacticEvent).filter(TacticEvent.incident_id == inc.id, TacticEvent.label == "THREAT_INTIMIDATION").first()
    assert threat.evidence_ref == f"utterance:{event.utterance_id}"


def test_order_bonus_needs_three_stages_in_canonical_order(db):
    # Demand, then threat, then authority: all three present but in reverse order, so no F2.
    _, analysis, ledger = analyse(db, "Caller: Transfer the security deposit to our account.\n"
                                      "Caller: You will be arrested.\n"
                                      "Caller: This is Inspector Rao from the Cyber Crime Cell.")
    assert not factor(ledger, "F2")
    assert sum(r.contribution for r in ledger) == analysis.risk_score == 6 + 14 + 18
    # Only two stages in order: still no F2.
    _, _, ledger2 = analyse(db, "Caller: You will be arrested.\nCaller: Transfer the security deposit to our account.")
    assert not factor(ledger2, "F2")


def test_ledger_always_sums_to_the_score(db):
    texts = [
        FULL, "Hi beta, dinner at eight.", "Never share your OTP. Visit your nearest branch.",
        "Please share the OTP you received. Pay Rs 5000 immediately or you will be arrested.",
        "Caller: This is the CBI. Do not tell anyone.\nVictim: Okay.\nCaller: Pay now to x@okaxis.",
    ]
    for text in texts:
        _, analysis, ledger = analyse(db, text)
        assert sum(r.contribution for r in ledger) == analysis.risk_score, text
        assert 0 <= analysis.risk_score <= 100


def test_victim_lines_add_no_risk(db):
    _, analysis, _ = analyse(db, "Caller: Good afternoon.\nVictim: Arrest? You will arrest me? Pay money? OTP?")
    assert analysis.risk_score == 0


def test_benign_advice_is_mitigated_only_when_nothing_is_requested(db):
    # Authority claim (+6) with official-channel advice and no payment request: M1 offsets it to 0.
    _, analysis, ledger = analyse(db, "This is the local police station calling about your passport verification. "
                                      "Please visit the station with original documents. No payment is required.")
    assert [r.contribution for r in factor(ledger, "F1")] == [6]
    assert [r.contribution for r in factor(ledger, "M1")] == [-6]   # limited to what was added: never below 0
    assert analysis.risk_score == 0

    # The same advice does not offset a scam that asks for money.
    _, scam, ledger2 = analyse(db, "This is the Cyber Crime Cell. Transfer the security deposit to our account. "
                                   "Never share your OTP with anyone.")
    assert not factor(ledger2, "M1")
    assert scam.risk_score >= 24


def test_weak_single_stage_is_mitigated(db):
    _, analysis, ledger = analyse(db, "Please note my badge number for reference.")
    assert [r.contribution for r in factor(ledger, "F1")] == [6]     # low-confidence authority rule (0.70)
    assert factor(ledger, "M2") and analysis.risk_score == 0


def test_uncertain_entity_extraction_is_mitigated(db):
    inc, _, _ = analyse(db, "This is the CBI. You will be arrested. Pay to scam@okaxis now.")
    ent = db.query(Entity).filter(Entity.type == "UPI_HANDLE").one()
    ev = db.query(Evidence).filter(Evidence.incident_id == inc.id).one()
    db.add(Mention(entity_id=ent.id, evidence_id=ev.id, span_start=0, span_end=1, extraction_confidence=0.4))
    db.commit()
    score, _, ledger = calculate_risk(db, inc.id)
    m3 = [c for c in ledger if c["factor"].startswith("M3")]
    assert m3 and m3[0]["contribution"] == -5
    assert score == sum(c["contribution"] for c in ledger)


def test_injection_flag_disables_all_mitigation(db):
    text = ("This is the local police station calling about your passport verification. "
            "Please visit the station with original documents. No payment is required.")
    inc, _, _ = analyse(db, text)
    flagged_score, _, flagged_ledger = calculate_risk(db, inc.id, injection_flagged=True)
    plain_score, _, _ = calculate_risk(db, inc.id, injection_flagged=False)
    assert not [c for c in flagged_ledger if c["effect"] == "MITIGATING"]
    assert flagged_score == 6 and plain_score == 0        # a flagged text never gets the benefit of the doubt
    assert flagged_score >= plain_score


def test_no_tactics_means_zero_with_empty_ledger(db):
    _, analysis, ledger = analyse(db, "Hi beta, are you coming home for dinner?")
    assert analysis.risk_score == 0 and ledger == []
