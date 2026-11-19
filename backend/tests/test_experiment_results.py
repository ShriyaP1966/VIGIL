"""The committed experiment results must be reproducible and consistent with the documents that quote them."""
import argparse
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import evaluate_model  # noqa: E402
import render_experiment_tables as tables  # noqa: E402

EXP = ROOT / "docs" / "experiments"
ROTATION = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))


def test_rotation_design_matches_the_preregistration():
    d = ROTATION["design"]
    assert d["rotation_levels"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert d["seeds"] == list(range(1001, 1011)) and len(d["seeds"]) >= 10
    assert d["t_candidate"] == 0.75
    assert len(ROTATION["runs"]) == 50
    assert ROTATION["calibration_tau_a"]["seed"] == 900 and ROTATION["calibration_tau_a"]["split"] == "dev"
    assert not set(d["seeds"]) & {900, 1}                          # no evaluation seed was used for calibration


def test_frozen_artefacts_are_unchanged_since_the_experiment_and_preregistration():
    prereg = (ROOT / "docs" / "PREREGISTRATION.md").read_text(encoding="utf-8")
    for path, digest in ROTATION["artefact_sha256_lf"].items():
        assert digest in prereg, f"{path}: the hash the experiment recorded is not the pre-registered one"
        assert evaluate_model.sha256_lf(ROOT / path) == digest, f"{path} changed after the experiment ran"
    sample = json.loads((EXP / "associations.json").read_text(encoding="utf-8"))["dataset"]["sha256_lf"]
    assert sample in prereg and evaluate_model.sha256_lf(ROOT / "data" / "scenarios.jsonl") == sample


def test_aggregates_are_recomputed_exactly_from_the_per_run_values():
    assert evaluate_model.aggregate_runs(ROTATION["runs"]) == ROTATION["aggregate"]
    assert evaluate_model.pooled_integrity(ROTATION["runs"]) == ROTATION["integrity_pooled"]


def test_every_run_holds_invariant_i1_and_no_observed_link_survives_on_a_benign_incident():
    for run in ROTATION["runs"]:
        assert run["integrity"]["i1_violations"] == 0
        assert run["integrity"]["observed_edges_touching_benign_after_counter_evidence"] == 0


def test_experiments_document_tables_are_generated_from_the_json():
    text = (ROOT / "docs" / "EXPERIMENTS.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert tables.render(text) == text, "docs/EXPERIMENTS.md is stale: run scripts/render_experiment_tables.py"


def test_readme_tables_are_generated_from_the_json():
    text = (ROOT / "README.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert tables.render(text, tables.README_SECTIONS) == text, "README.md is stale: run scripts/render_experiment_tables.py"


def test_readme_states_the_held_out_result_and_its_limits_plainly():
    """The README must not soften the held-out false alarms, and must carry the required caveats."""
    import json as _json
    held = _json.loads((EXP / "heldout.json").read_text(encoding="utf-8"))["metrics"]["scenario_level"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"{held['scam_scenarios_detected']} of {held['scam_scenarios']} scam scenarios" in readme
    assert f"{held['legitimate_false_alarms']} of {held['legitimate_scenarios']}" in readme
    for needle in ("H21", "H15", "H17", "wording, not intent", "unverified", "not measured", "small", "synthetic",
                   "were **not** changed afterwards", "speaker's role and intent", "drafted by a different language model"):
        assert needle in readme, needle
    assert "T_CANDIDATE = 0.75" in readme and "Post-hoc" in readme            # the headline and the post-hoc row are labelled


def test_chart_exists_and_is_small():
    for name in ("rotation_all.png", "rotation_test.png"):
        size = (EXP / name).stat().st_size
        assert 0 < size < 200_000, f"{name} is {size} bytes"


def test_committed_entities_result_is_reproducible():
    committed = json.loads((EXP / "entities_all.json").read_text(encoding="utf-8"))
    fresh = evaluate_model.suite_entities(argparse.Namespace(data=ROOT / "data" / "scenarios.jsonl", split="all"))
    assert fresh["metrics"] == committed["metrics"]


@pytest.mark.slow
def test_one_rotation_run_is_reproduced_exactly():
    """Seed 1001 at r = 0.5 through the real pipeline gives the stored numbers (the full experiment takes ~40 min)."""
    stored = next(r for r in ROTATION["runs"] if r["seed"] == 1001 and r["rotation"] == 0.5)
    tau = ROTATION["calibration_tau_a"]["chosen_tau_a"]
    assert evaluate_model._run_one((1001, 0.5, tau)) == stored
