"""Dataset generator v1, its validator, and reproducibility of the committed evaluation results."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import evaluate_model  # noqa: E402
import generate_dataset as gen  # noqa: E402

DATA = ROOT / "data" / "scenarios.jsonl"


@pytest.fixture(scope="module")
def records():
    return gen.generate(seed=1, rotation=0.5)


def test_committed_dataset_is_exactly_what_the_command_produces(records):
    assert gen.load(DATA) == records, "data/scenarios.jsonl is stale: run python scripts/generate_dataset.py --seed 1"
    assert DATA.stat().st_size < gen.MAX_BYTES


def test_generation_is_deterministic_and_seed_dependent(records):
    assert gen.generate(1, 0.5) == records
    assert gen.generate(2, 0.5) != records


def test_composition_matches_the_plan(records):
    campaign = [r for r in records if r["scenario_type"] != "legitimate"]
    negatives = [r for r in records if r["scenario_type"] == "legitimate"]
    assert len(campaign) == 72 and len(negatives) == 40
    assert Counter(r["campaign_template_id"] for r in campaign) == {t: 12 for t in gen.TEMPLATES}
    assert all(r["is_synthetic"] is True for r in records)


def test_validator_accepts_the_generated_data(records):
    assert gen.validate(records) == []


def test_splits_are_by_template_with_no_template_in_two_splits(records):
    splits_by_template = {}
    for r in records:
        splits_by_template.setdefault(r["campaign_template_id"], set()).add(r["split"])
    assert all(len(s) == 1 for s in splits_by_template.values())
    assert {next(iter(splits_by_template[t])) for t in ("T1", "T4")} == {"train"}
    assert {next(iter(splits_by_template[t])) for t in ("T2", "T5")} == {"dev"}
    assert {next(iter(splits_by_template[t])) for t in ("T3", "T6")} == {"test"}


def test_a_handful_of_hindi_and_marathi_incidents_exist(records):
    langs = Counter(r["language"] for r in records)
    assert langs["hi"] == 2 and langs["mr"] == 2
    assert {r["split"] for r in records if r["language"] == "mr"} == {"test"}


def test_rotation_parameter_controls_identifier_reuse():
    def instances(rotation):
        out = {}
        for r in gen.generate(1, rotation):
            if r["campaign_instance_id"]:
                out.setdefault(r["campaign_instance_id"], []).append(r["identifiers"])
        return out

    for chain in instances(0.0).values():
        assert all(ids == chain[0] for ids in chain)               # r = 0: identifiers never change
    for chain in instances(1.0).values():
        for prev, nxt in zip(chain, chain[1:]):
            assert all(prev[k] != nxt[k] for k in prev)            # r = 1: every identifier is replaced


def test_ground_truth_pairs_are_symmetric_and_only_within_an_instance(records):
    by_id = {r["incident_id"]: r for r in records}
    for r in records:
        for other in r["expected_associations"]:
            assert r["incident_id"] in by_id[other]["expected_associations"]
            assert by_id[other]["campaign_instance_id"] == r["campaign_instance_id"]
        if r["scenario_type"] == "legitimate":
            assert r["expected_associations"] == []


def test_utterance_labels_use_the_vocabulary_and_victims_carry_none(records):
    from ai_engine.extraction.tactics import TACTIC_LABELS
    for r in records:
        for u in r["utterances"]:
            assert set(u["tactic_labels"]) <= set(TACTIC_LABELS)
            if u["speaker"] == "victim":
                assert u["tactic_labels"] == []


# ---------------------------------------------------------------------------------------------
# The validator must actually reject bad data
# ---------------------------------------------------------------------------------------------

def mutate(records, fn):
    bad = json.loads(json.dumps(records[:3]))
    fn(bad[0])
    return gen.validate(bad)


def test_validator_rejects_secret_like_text():
    errs = mutate(gen.generate(1, 0.5), lambda r: r["utterances"][0].update(text="Your OTP is 482913, share it"))
    assert any("secret" in e for e in errs)


def test_validator_rejects_non_synthetic_identifiers_and_flags():
    recs = gen.generate(1, 0.5)
    assert any("phone" in e for e in mutate(recs, lambda r: r["identifiers"].update(phone="+91 90123 45678")))
    assert any("domain" in e for e in mutate(recs, lambda r: r["identifiers"].update(domain="real-bank.com")))
    assert any("upi" in e for e in mutate(recs, lambda r: r["identifiers"].update(upi="someone@realbank")))
    assert any("is_synthetic" in e for e in mutate(recs, lambda r: r.update(is_synthetic=False)))


def test_validator_rejects_bad_structure():
    recs = gen.generate(1, 0.5)
    assert any("missing" in e for e in mutate(recs, lambda r: r.pop("split")))
    assert any("splits are by template" in e for e in mutate(recs, lambda r: r.update(split="test")))
    assert any("unknown labels" in e for e in mutate(recs, lambda r: r["utterances"][0].update(tactic_labels=["MADE_UP"])))
    assert any("language" in e for e in mutate(recs, lambda r: r.update(language="fr")))


# ---------------------------------------------------------------------------------------------
# Evaluation: metric arithmetic and reproducibility of the committed result files
# ---------------------------------------------------------------------------------------------

def test_prf_arithmetic():
    m = evaluate_model.prf(tp=8, fp=2, fn=2)
    assert (m["precision"], m["recall"]) == (0.8, 0.8) and round(m["f1"], 4) == 0.8
    assert evaluate_model.prf(0, 0, 0)["f1"] is None            # no support: not scored, never faked as 0 or 1
    assert evaluate_model.prf(0, 3, 0)["f1"] == 0.0


@pytest.mark.parametrize("split", ["train", "dev", "test"])
def test_committed_tactics_results_are_reproducible(split):
    committed = json.loads((ROOT / "docs" / "experiments" / f"tactics_{split}.json").read_text(encoding="utf-8"))
    fresh = evaluate_model.suite_tactics(argparse.Namespace(data=DATA, split=split))
    assert fresh["metrics"] == committed["metrics"], "docs/experiments is stale: re-run evaluate_model.py"
    assert fresh["dataset"] == committed["dataset"] and fresh["extractor"] == committed["extractor"]


def test_committed_injection_result_is_reproducible():
    committed = json.loads((ROOT / "docs" / "experiments" / "injection.json").read_text(encoding="utf-8"))
    fresh = evaluate_model.suite_injection(argparse.Namespace())
    assert fresh["metrics"] == committed["metrics"] and fresh["per_attack"] == committed["per_attack"]
    assert fresh["metrics"]["total"] == 10
