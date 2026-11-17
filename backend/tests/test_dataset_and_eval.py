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
    campaign = [r for r in records if r["scenario_type"] not in ("legitimate", "decoy")]
    negatives = [r for r in records if r["scenario_type"] == "legitimate"]
    decoys = [r for r in records if r["scenario_type"] == "decoy"]
    assert (len(campaign), len(negatives), len(decoys)) == (90, 40, 20)
    assert Counter(r["campaign_template_id"] for r in campaign) == {t: 15 for t in gen.TEMPLATES}
    assert Counter(r["decoy_type"] for r in decoys) == {t: 5 for t in gen.DECOY_TYPES.values()}
    assert all(r["is_synthetic"] is True for r in records)


def test_decoys_are_never_in_a_ground_truth_pair(records):
    for r in records:
        if r["scenario_type"] in ("legitimate", "decoy"):
            assert r["campaign_instance_id"] is None and r["script_family"] is None
            assert r["expected_associations"] == []


def test_script_family_map_is_by_scam_type_and_fixed(records):
    """Ground truth (b): decided before any experiment. T1+T2+T3 are one family; T4 and T5 are NOT merged."""
    assert gen.FAMILY_OF == {"T1": "digital_arrest", "T2": "digital_arrest", "T3": "digital_arrest",
                             "T4": "bank_kyc", "T5": "payment_link", "T6": "courier_customs"}
    for r in records:
        if r["campaign_instance_id"]:
            assert r["script_family"] == gen.FAMILY_OF[r["campaign_template_id"]]


def test_every_identifier_is_unique_per_instance_chain_and_never_shared_across_instances():
    """A shared identifier must always be deliberate (r = 0 reuse within an instance), never a random collision."""
    for rotation in (0.0, 0.5, 1.0):
        owner: dict[str, str] = {}
        for r in gen.generate(7, rotation):
            for value in r["identifiers"].values():
                assert owner.setdefault(value, r["campaign_instance_id"] or r["incident_id"]) == \
                    (r["campaign_instance_id"] or r["incident_id"])


def test_decoy_types_have_the_properties_the_blueprint_asks_for(records):
    from ai_engine.fingerprint.similarity import order_consistency
    d = {t: [r for r in records if r["decoy_type"] == name] for t, name in gen.DECOY_TYPES.items()}
    # D3: scam-like stages in an order that is mostly incompatible with the canonical script
    canonical = ["AUTHORITY", "ALLEGATION", "THREAT", "ISOLATION", "URGENCY", "DEMAND"]
    for r in d["D3"]:
        assert sorted(r["expected_stage_sequence"]) == sorted(canonical)
        assert order_consistency(tuple(canonical), tuple(r["expected_stage_sequence"])) <= 0.4
    # D2 cites an official public identifier; D4 has no extractable identifier and no clear stage
    assert all("1930" in r["utterances"][0]["text"] or "cybercrime.gov.in" in r["utterances"][0]["text"] for r in d["D2"])
    assert all(r["expected_stage_sequence"] == [] and r["entity_mentions"] == [] for r in d["D4"])
    assert all(r["utterances"][0]["tactic_labels"] == [] for r in d["D1"] + d["D2"] + d["D4"] if r["utterances"])


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
        if r["scenario_type"] in ("legitimate", "decoy"):
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
    assert any("script_family" in e for e in mutate(recs, lambda r: r.update(script_family="bank_kyc")))
    assert any("decoy_type" in e for e in mutate(recs, lambda r: r.update(decoy_type="benign_shared_identifier")))


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
