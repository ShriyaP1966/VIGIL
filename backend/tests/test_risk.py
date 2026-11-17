"""Placeholder risk heuristic (Phase 1): ledger exactness and cue hygiene."""
import pytest

from backend.app.schemas.schemas import IncidentCreate, EvidenceCreate
from backend.app.services.incident_service import create_incident, run_incident_analysis
from backend.app.services.risk_service import calculate_baseline_risk, risk_band_for
from backend.app.models.models import RiskContribution


@pytest.fixture
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _risk(db, text):
    inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(text=text)]))
    return calculate_baseline_risk(db, inc.id)


@pytest.mark.parametrize("score,band", [
    (0, "LOW"), (29, "LOW"), (30, "ELEVATED"), (59, "ELEVATED"),
    (60, "HIGH"), (79, "HIGH"), (80, "CRITICAL"), (100, "CRITICAL"),
])
def test_band_boundaries(score, band):
    assert risk_band_for(score) == band


def test_word_boundary_cues_do_not_fire_inside_other_words(db):
    # "confirm" and "first" contain "fir"; they are not legal threats.
    score, band, contribs = _risk(db, "Please confirm your first appointment at the branch.")
    assert score == 0 and contribs == []


def test_bank_mention_alone_is_not_authority_impersonation(db):
    score, _, contribs = _risk(db, "Your HDFC Bank statement is ready. Visit your nearest branch.")
    assert not any("Authority" in c["factor"] for c in contribs)
    assert score == 0


def test_authority_plus_threat_scores_and_cites_matching_evidence(db):
    inc = create_incident(db, IncidentCreate(title="t", evidence=[
        EvidenceCreate(text="Hello, how are you today."),
        EvidenceCreate(text="This is CBI. A warrant will be issued immediately."),
    ]))
    score, band, contribs = calculate_baseline_risk(db, inc.id)
    factors = {c["factor"]: c for c in contribs}
    threat = next(v for k, v in factors.items() if "Threat" in k)
    urgency = next(v for k, v in factors.items() if "Urgency" in k)
    second_ev = inc.evidence_items[1].id
    assert threat["evidence_ref"] == f"evidence:{second_ev}"   # cites the evidence that matched, not the first one
    assert urgency["evidence_ref"] == f"evidence:{second_ev}"
    assert score == sum(c["contribution"] for c in contribs) == 14 + 14 + 8


def test_benign_cues_mitigate_but_never_below_zero(db):
    score, _, contribs = _risk(db, "Official website notice: warrant not issued. Visit your nearest branch.")
    assert score >= 0
    assert score == sum(c["contribution"] for c in contribs)
    assert any(c["factor"].startswith("M1") for c in contribs)


def test_no_benign_mitigation_when_payment_handle_requested(db):
    _, _, contribs = _risk(db, "Visit your nearest branch or just pay to scam@okaxis immediately.")
    assert not any(c["factor"].startswith("M1") for c in contribs)


def test_persisted_contributions_sum_to_stored_score(db):
    inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(
        text="CBI officer: arrest warrant, pay immediately to x@okaxis or visit https://fake.example/pay")]))
    analysis = run_incident_analysis(db, inc.id)
    rows = db.query(RiskContribution).filter(RiskContribution.analysis_id == analysis.id).all()
    assert rows
    assert sum(r.contribution for r in rows) == analysis.risk_score
    for r in rows:
        assert r.factor and r.explanation and r.rule_version and r.effect in {"SUPPORTING", "MITIGATING"}
        assert (r.effect == "SUPPORTING") == (r.contribution > 0)
