"""Playbook fingerprint similarity (blueprint §6.7): formula, gate, partial calls, symmetry, determinism."""
import itertools

import pytest

from ai_engine.extraction.tactics import CANONICAL_STAGES
from ai_engine.fingerprint.similarity import (
    DEFAULT_T_CANDIDATE, Fingerprint, compare, lcs_length, order_consistency,
)

FULL = tuple(CANONICAL_STAGES)   # AUTHORITY, ALLEGATION, THREAT, ISOLATION, URGENCY, DEMAND


def fp(seq, inst="CENTRAL_AGENCY", pay="UPI", **kw):
    return Fingerprint(sequence=tuple(seq), institution_class=inst, payment_channel=pay, **kw)


def test_default_threshold_is_the_blueprint_value():
    assert DEFAULT_T_CANDIDATE == 0.75


def test_lcs_and_order_helpers():
    assert lcs_length(("A", "B", "C"), ("A", "C")) == 2
    assert lcs_length((), ("A",)) == 0
    assert lcs_length(("A", "B", "C"), ("C", "B", "A")) == 1
    assert order_consistency(("A", "B", "C"), ("A", "B", "C")) == 1.0
    assert order_consistency(("A", "B", "C"), ("C", "B", "A")) == 0.0
    assert order_consistency(("A", "B", "C"), ("A", "C", "B")) == pytest.approx(2 / 3)   # 2 of 3 pairs agree
    assert order_consistency(("A",), ("A",)) == 1.0 and order_consistency(("A",), ("B",)) == 0.0


def test_identical_full_playbooks_score_one():
    r = compare(fp(FULL), fp(FULL))
    assert r.gate_passed and r.playbook_sim == pytest.approx(1.0) and r.is_candidate
    assert r.lcs == 6 and r.seq_sim == pytest.approx(1.0)


def test_formula_with_different_institution_same_payment():
    # seq_sim = 1, inst_match = 0, pay_match = 1  ->  (0.65*1 + 0.15*0 + 0.10*1) / 0.90
    r = compare(fp(FULL, inst="CENTRAL_AGENCY"), fp(FULL, inst="TELECOM"))
    assert r.playbook_sim == pytest.approx((0.65 + 0.10) / 0.90)
    assert r.inst_match == 0.0 and r.pay_match == 1.0
    assert r.is_candidate                                  # 0.833 >= 0.75


def test_unknown_values_are_half_credit():
    r = compare(fp(FULL, inst="UNKNOWN", pay="NONE"), fp(FULL, inst="POLICE", pay="UPI"))
    assert r.inst_match == 0.5 and r.pay_match == 0.5
    assert compare(fp(FULL, pay="UNKNOWN"), fp(FULL, pay="UNKNOWN")).pay_match == 1.0   # equal beats unknown


def test_cut_off_call_matches_through_containment():
    # A call cut off after isolation: 4 of 6 stages, same order.
    r = compare(fp(FULL), fp(FULL[:4]))
    seq = 0.40 * (4 / 6) + 0.30 * 1.0 * min(1, 4 / 4) + 0.30 * 1.0
    assert r.gate_passed and r.lcs == 4
    assert r.containment == 1.0 and r.containment_adj == 1.0
    assert r.playbook_sim == pytest.approx((0.65 * seq + 0.15 + 0.10) / 0.90)
    assert r.is_candidate


def test_short_fragment_is_damped_but_can_still_pass():
    # 3 stages: containment is 1.0 but is damped by 3/4.
    r = compare(fp(FULL), fp(FULL[:3]))
    seq = 0.40 * (3 / 6) + 0.30 * (1.0 * 3 / 4) + 0.30 * 1.0
    assert r.containment_adj == pytest.approx(0.75)
    assert r.playbook_sim == pytest.approx((0.65 * seq + 0.25) / 0.90)
    # Damping really matters: with a different institution and payment the same fragment falls short.
    weak = compare(fp(FULL), fp(FULL[:3], inst="BANK", pay="LINK_PAYMENT"))
    assert weak.gate_passed and not weak.is_candidate


def test_gate_rejects_fragments_with_fewer_than_three_stages():
    r = compare(fp(FULL), fp(FULL[:2]))
    assert not r.gate_passed and not r.is_candidate
    assert "fewer than 3" in r.gate_reason
    assert r.playbook_sim > 0   # the score is still reported for diagnostics, but never creates a candidate


def test_gate_rejects_sequences_without_a_common_run_of_three():
    a = fp(("AUTHORITY", "ALLEGATION", "THREAT"))
    b = fp(("THREAT", "ALLEGATION", "AUTHORITY"))          # same stages, opposite order: LCS is only 1
    r = compare(a, b)
    assert not r.gate_passed and r.lcs == 1 and "shorter than 3" in r.gate_reason
    assert r.order_ok == 0.0 and not r.is_candidate


def test_authority_claim_only_legitimate_call_fails_the_gate():
    legit = fp(("AUTHORITY",), inst="POLICE", pay="NONE")
    assert not compare(fp(FULL), legit).is_candidate
    assert not compare(legit, legit).is_candidate          # even identical single-stage calls never link


def test_different_scam_types_fall_below_the_threshold():
    kyc = fp(("AUTHORITY", "ALLEGATION", "THREAT", "URGENCY"), inst="BANK", pay="LINK_PAYMENT")
    arrest = fp(FULL, inst="CENTRAL_AGENCY", pay="UPI")
    r = compare(kyc, arrest)
    assert r.gate_passed and not r.is_candidate and r.playbook_sim < DEFAULT_T_CANDIDATE


def test_language_and_channel_never_change_the_score():
    base = compare(fp(FULL, language="en", channel="call"), fp(FULL, language="en", channel="call"))
    other = compare(fp(FULL, language="hi-Latn", channel="call"), fp(FULL, language="mr", channel="sms"))
    assert base == other   # all fields identical, including playbook_sim


def test_symmetric_bounded_and_deterministic():
    seqs = [FULL, FULL[:4], FULL[1:], ("AUTHORITY", "THREAT", "DEMAND"), ("DEMAND", "THREAT", "AUTHORITY"),
            ("AUTHORITY", "ALLEGATION")]
    insts = ["CENTRAL_AGENCY", "BANK", "UNKNOWN"]
    pays = ["UPI", "NONE", "LINK_PAYMENT"]
    for (sa, ia, pa), (sb, ib, pb) in itertools.product(itertools.product(seqs, insts, pays), repeat=2):
        a, b = fp(sa, ia, pa), fp(sb, ib, pb)
        ab, ba = compare(a, b), compare(b, a)
        assert ab.playbook_sim == pytest.approx(ba.playbook_sim)
        assert ab.gate_passed == ba.gate_passed and ab.is_candidate == ba.is_candidate
        assert 0.0 <= ab.playbook_sim <= 1.0 + 1e-12
        assert compare(a, b) == ab


def test_threshold_is_a_parameter_not_a_constant():
    a, b = fp(FULL), fp(FULL, inst="TELECOM")               # playbook_sim = 0.8333
    assert compare(a, b, t_candidate=0.75).is_candidate
    assert not compare(a, b, t_candidate=0.90).is_candidate
    assert compare(a, b, t_candidate=0.90).t_candidate == 0.90


def test_from_json_reads_the_stored_fingerprint():
    f = Fingerprint.from_json({"stage_sequence": ["AUTHORITY", "THREAT"], "institution_class": "POLICE",
                               "payment_channel": "UPI", "language": "en", "channel": "call"})
    assert f.sequence == ("AUTHORITY", "THREAT") and f.institution_class == "POLICE"
    empty = Fingerprint.from_json({})
    assert empty.sequence == () and empty.institution_class == "UNKNOWN"
    assert not compare(empty, empty).gate_passed
