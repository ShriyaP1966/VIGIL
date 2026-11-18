"""Metric arithmetic, arm construction and the held-out guard for the Phase 5 experiments.

These tests use hand-computed toy cases and a 16-incident replay; they do not read the owner's held-out file and
they do not look at any evaluation seed."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import eval_metrics as em  # noqa: E402
import evaluate_model  # noqa: E402
import generate_dataset as gen  # noqa: E402
from backend.app.services.replay_service import Edge, ReplayResult, replay_records  # noqa: E402


def edge(a, b, status="OBSERVED_MATCH", match_type="EXACT_IDENTIFIER", shared=("PHONE:+919876500001",)):
    return Edge(a, b, status, match_type, tuple(shared), 0.7, None)


# ---------------------------------------------------------------------------------------------
# metric arithmetic (computed by hand)
# ---------------------------------------------------------------------------------------------

def test_components_union_find_and_singletons():
    comp = em.components(["a", "b", "c", "d", "e"], [("a", "b"), ("b", "c")])
    assert comp["a"] == comp["b"] == comp["c"] and comp["d"] != comp["e"] and comp["d"] != comp["a"]
    assert em.components(["x"], [("x", "ghost")]) == {"x": "x"}        # edges to unknown incidents are ignored


def test_pairwise_counts_precision_recall_f1_and_false_association_rate():
    ids = ["a", "b", "c", "d"]
    truth = lambda i, j: {i, j} in ({"a", "b"}, {"c", "d"})           # noqa: E731  two true pairs
    comp = em.components(ids, [("a", "b"), ("b", "c")])               # predicts {a,b,c}: ab (TP), bc, ac (FP)
    m = em.pairwise(ids, comp, truth, benign={"d"})
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (1, 2, 1, 2)       # cd is a miss; ad, bd are correct non-links
    assert m["precision"] == pytest.approx(1 / 3) and m["recall"] == pytest.approx(1 / 2)
    assert m["f1"] == pytest.approx(0.4)
    assert m["far"] == pytest.approx(2 / 4)                            # non-pairs: ac, bc, ad, bd -> 2 linked
    assert m["far_benign"] == 0.0                                      # non-pairs touching d: ad, bd, neither linked


def test_undefined_values_are_none_never_zero_or_one():
    ids = ["a", "b", "c"]
    none_true = em.pairwise(ids, em.components(ids, []), lambda i, j: False, set())
    assert none_true["precision"] is None and none_true["recall"] is None and none_true["f1"] is None
    assert none_true["far"] == 0.0
    missed = em.pairwise(ids, em.components(ids, []), lambda i, j: {i, j} == {"a", "b"}, set())
    assert missed["precision"] is None and missed["recall"] == 0.0 and missed["f1"] == 0.0   # true pair, no prediction
    all_true = em.pairwise(ids, em.components(ids, [("a", "b"), ("b", "c")]), lambda i, j: True, set())
    assert all_true["far"] is None                                      # no non-pairs at all


def test_candidate_precision_and_recall():
    ids = ["a", "b", "c", "d"]
    truth = lambda i, j: {i, j} in ({"a", "b"}, {"c", "d"})           # noqa: E731
    comp_c = em.components(ids, [("a", "b")])                          # C connects ab only
    cands = [("c", "d"), ("a", "c")]                                   # one right, one wrong
    comp_d = em.components(ids, [("a", "b")] + cands)
    s = em.candidate_scores(ids, cands, comp_c, comp_d, truth)
    assert s["candidate_precision"] == 0.5
    assert (s["uncovered_true_pairs"], s["recovered_by_candidates"], s["candidate_recall"]) == (1, 1, 1.0)
    none = em.candidate_scores(ids, [], comp_c, comp_c, truth)
    assert none["candidate_precision"] is None and none["candidate_recall"] == 0.0


def test_mean_std_is_the_sample_std_over_defined_values():
    assert em.mean_std([1.0, 2.0, 3.0, None]) == {"mean": 2.0, "std": 1.0, "n": 3}
    assert em.mean_std([None, None]) == {"mean": None, "std": None, "n": 0}
    assert em.mean_std([5.0])["std"] is None


def test_ground_truth_functions_use_instance_and_family():
    recs = [
        {"incident_id": "x1", "campaign_instance_id": "T1-c1", "script_family": "digital_arrest", "scenario_type": "k"},
        {"incident_id": "x2", "campaign_instance_id": "T1-c2", "script_family": "digital_arrest", "scenario_type": "k"},
        {"incident_id": "x3", "campaign_instance_id": "T4-c1", "script_family": "bank_kyc", "scenario_type": "k"},
        {"incident_id": "x4", "campaign_instance_id": "T5-c1", "script_family": "payment_link", "scenario_type": "k"},
        {"incident_id": "n1", "campaign_instance_id": None, "script_family": None, "scenario_type": "legitimate"},
        {"incident_id": "n2", "campaign_instance_id": None, "script_family": None, "scenario_type": "legitimate"},
    ]
    t = em.truth_functions(recs)
    assert not t["a"]("x1", "x2") and t["b"]("x1", "x2")                # same family, different instance
    assert not t["b"]("x3", "x4")                                       # T4 and T5 are NOT merged
    assert not t["a"]("n1", "n2") and not t["b"]("n1", "n2")            # negatives are never pairs
    assert em.benign_ids(recs) == {"n1", "n2"}


def test_arm_edge_selectors_follow_the_preregistered_definitions():
    edges = [
        edge("a", "b"),                                                           # observed identifier link
        edge("c", "d", status="DISPUTED_ASSOCIATION"),                            # identifier link the rules disputed
        edge("e", "f", status="CANDIDATE_ASSOCIATION", match_type="PLAYBOOK", shared=()),
        edge("g", "h", status="DISPUTED_ASSOCIATION", match_type="PLAYBOOK", shared=()),
        edge("i", "j", status="OBSERVED_MATCH", match_type="COMBINED"),
    ]
    assert em.edges_b(edges) == [("a", "b"), ("c", "d"), ("i", "j")]            # counter-evidence not applied
    assert em.edges_c(edges) == [("a", "b"), ("i", "j")]                        # disputed links are gone
    assert em.edges_d(edges) == [("a", "b"), ("e", "f"), ("i", "j")]            # + candidates, never disputed ones
    assert em.edges_candidate(edges) == [("e", "f")]


# ---------------------------------------------------------------------------------------------
# arm A (text baseline)
# ---------------------------------------------------------------------------------------------

def _rec(iid, *texts, speaker="caller"):
    return {"incident_id": iid, "utterances": [{"idx": i, "speaker": speaker, "text": t} for i, t in enumerate(texts)]}


def test_arm_a_links_similar_text_and_only_incidents_with_a_scam_label():
    scam = "This is an officer from the CBI. You will be arrested today, do not tell anyone. Pay immediately."
    recs = [_rec("s1", scam), _rec("s2", scam + " Thank you."),
            _rec("ok", "Hi beta, are you coming home for dinner?")]
    gated = evaluate_model.scam_gate(recs)
    assert gated == {"s1", "s2"}                                       # the family call is not classified as a scam
    ids, sim = evaluate_model.arm_a_similarities(recs, gated)
    assert evaluate_model.arm_a_edges(ids, sim, 0.5) == [("s1", "s2")]
    assert evaluate_model.arm_a_edges(ids, sim, 0.999999) == []         # a threshold above the similarity links nothing
    assert evaluate_model.arm_a_edges(*evaluate_model.arm_a_similarities(recs, {"s1"}), 0.1) == []   # one incident


def test_tau_a_calibration_uses_dev_only_and_the_declared_seed():
    cal = evaluate_model.calibrate_tau_a()
    assert (cal["seed"], cal["rotation"], cal["split"], cal["ground_truth"]) == (900, 0.5, "dev", "a")
    assert cal["chosen_tau_a"] in evaluate_model.TAU_GRID and len(cal["table"]) == len(evaluate_model.TAU_GRID)
    assert cal["incidents"] > 0
    best = max(cal["table"], key=lambda row: ((row["f1"] or 0.0), row["tau"]))
    assert best["tau"] == cal["chosen_tau_a"]                          # ties go to the larger tau


# ---------------------------------------------------------------------------------------------
# integrity counters on a fake result
# ---------------------------------------------------------------------------------------------

def test_integrity_counts_flag_observed_links_without_shared_identifiers():
    recs = [
        {"incident_id": "c1", "scenario_type": "digital_arrest_cbi", "decoy_type": None,
         "utterances": [{"speaker": "caller", "text": "Pay to verify11@okaxis now", "idx": 0}]},
        {"incident_id": "c2", "scenario_type": "digital_arrest_cbi", "decoy_type": None,
         "utterances": [{"speaker": "caller", "text": "Pay to verify11@okaxis today", "idx": 0}]},
        {"incident_id": "n1", "scenario_type": "legitimate", "decoy_type": None,
         "utterances": [{"speaker": "sender", "text": "Statement ready", "idx": 0}]},
    ]
    good = ReplayResult(edges=[edge("c1", "c2", shared=("UPI_HANDLE:verify11@okaxis",))],
                        campaigns=[{"members": ["c1", "c2"], "confidence": 0.75, "status": "x", "bases": ["OBSERVED"]}])
    assert evaluate_model.association_integrity(recs, good)["i1_violations"] == 0
    bad = ReplayResult(edges=[edge("c1", "n1", shared=("UPI_HANDLE:verify11@okaxis",)),     # n1 never mentions it
                              edge("c1", "c2", shared=())])                                 # no shared identifier at all
    out = evaluate_model.association_integrity(recs, bad)
    assert out["i1_violations"] == 2
    assert out["observed_edges_touching_benign_after_counter_evidence"] == 1
    assert out["negatives_with_observed_edge"] == 1


# ---------------------------------------------------------------------------------------------
# arms B and C are read from one run: that must equal running the pipeline with the feature switched off
# ---------------------------------------------------------------------------------------------

def test_arms_read_from_one_run_equal_the_ablated_pipelines():
    records = gen.generate(900, 0.5)                                    # seed 900: dev-only debugging seed
    pick = [r for r in records if r["campaign_instance_id"] in ("T1-c1", "T1-c2", "T4-c1")]
    pick += [r for r in records if r["campaign_template_id"] == "N1"][:4]
    pick += [r for r in records if r["campaign_template_id"] == "D2"][:3]
    full = replay_records(pick)
    no_ce = replay_records(pick, counter_evidence=False)
    no_cand = replay_records(pick, candidates=False)
    assert set(em.edges_b(full.edges)) == set(em.edges_b(no_ce.edges)), "B must not depend on counter-evidence"
    assert set(em.edges_c(full.edges)) == set(em.edges_c(no_cand.edges)), "C must not depend on candidates"
    assert not em.edges_candidate(no_cand.edges)                        # candidates really are switched off
    assert not any(e.status == "DISPUTED_ASSOCIATION" for e in no_ce.edges)   # counter-evidence really is switched off
    assert set(em.edges_c(full.edges)) <= set(em.edges_b(full.edges))
    assert set(em.edges_c(full.edges)) <= set(em.edges_d(full.edges))
    assert evaluate_model.association_integrity(pick, full)["i1_violations"] == 0
    assert replay_records(pick).edges == full.edges                     # deterministic


# ---------------------------------------------------------------------------------------------
# held-out set guard (uses temporary files only; the owner's file is never read here)
# ---------------------------------------------------------------------------------------------

HELDOUT_ROW = {"id": "H01", "source_channel": "call", "language": "en", "is_legitimate": False, "utterances": [
    {"speaker": "caller", "text": "This is the CBI. You will be arrested today, transfer money now.",
     "tactic_labels": ["AUTHORITY_IMPERSONATION", "THREAT_INTIMIDATION"]}]}


def test_heldout_refuses_an_empty_file_and_a_second_run(tmp_path):
    empty = tmp_path / "heldout.jsonl"
    empty.write_text("\n# comment only\n", encoding="utf-8")
    with pytest.raises(evaluate_model.HeldoutRefused, match="empty"):
        evaluate_model.suite_heldout(None, path=empty, result_path=tmp_path / "heldout.json")

    full = tmp_path / "full.jsonl"
    full.write_text(json.dumps(HELDOUT_ROW) + "\n", encoding="utf-8")
    result_path = tmp_path / "result.json"
    result = evaluate_model.suite_heldout(None, path=full, result_path=result_path)
    assert result["dataset"]["scenarios"] == 1
    result_path.write_text("{}", encoding="utf-8")                     # the first result now exists
    with pytest.raises(evaluate_model.HeldoutRefused, match="once"):
        evaluate_model.suite_heldout(None, path=full, result_path=result_path)


def test_heldout_validates_labels_and_fields(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({**HELDOUT_ROW, "utterances": [
        {"speaker": "caller", "text": "x", "tactic_labels": ["MADE_UP"]}]}), encoding="utf-8")
    with pytest.raises(evaluate_model.HeldoutRefused, match="unknown tactic labels"):
        evaluate_model.load_heldout(bad)
    missing = tmp_path / "missing.jsonl"
    missing.write_text(json.dumps({"id": "H02"}), encoding="utf-8")
    with pytest.raises(evaluate_model.HeldoutRefused, match="missing field"):
        evaluate_model.load_heldout(missing)


def test_heldout_without_gold_tactic_labels_reports_only_scenario_level_numbers(tmp_path):
    """The owner's file carries no per-utterance tactic labels: tactic-level scores must be reported as not measured,
    and scam detection / false alarms are counted per scenario. (Toy scenarios here, never the owner's file.)"""
    scam = {"id": "T1", "source_channel": "call", "language": "en", "is_legitimate": False, "notes": "type: toy scam; group: none",
            "utterances": [{"speaker": "caller", "text": "This is the CBI. You will be arrested today, transfer money now.", "tactic_labels": []}]}
    fine = {"id": "T2", "source_channel": "sms", "language": "en", "is_legitimate": True, "notes": "type: legitimate",
            "utterances": [{"speaker": "sender", "text": "Your statement has been generated. Visit your branch.", "tactic_labels": []}]}
    quiet_scam = {"id": "T3", "source_channel": "sms", "language": "en", "is_legitimate": False, "notes": "type: toy quiet",
                  "utterances": [{"speaker": "sender", "text": "Hello, please call us back.", "tactic_labels": []}]}
    f = tmp_path / "unlabelled.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in (scam, fine, quiet_scam)) + "\n", encoding="utf-8")
    result = evaluate_model.suite_heldout(None, path=f, result_path=tmp_path / "r.json")
    m = result["metrics"]
    assert m["tactic_level"].startswith("not measured")
    assert "macro_f1_over_labels_with_support" not in m and "per_label" not in m
    s = m["scenario_level"]
    assert (s["scam_scenarios"], s["scam_scenarios_detected"], s["scam_detection_rate"]) == (2, 1, 0.5)
    assert (s["legitimate_scenarios"], s["legitimate_false_alarms"], s["legitimate_false_alarm_rate"]) == (1, 0, 0.0)
    assert [(p["id"], p["scam_tactic_detected"]) for p in result["per_scenario"]] == [("T1", True), ("T2", False), ("T3", False)]
    assert result["per_scenario"][0]["type"] == "toy scam"
