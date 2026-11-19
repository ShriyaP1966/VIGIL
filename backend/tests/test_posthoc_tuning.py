"""The post-hoc tuned variant: its edge rules, the claim that a higher threshold can be read from a run at 0.75, and
that the committed files follow the protocol and leave the pre-registered headline alone."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import eval_metrics as em  # noqa: E402
import generate_dataset as gen  # noqa: E402
import posthoc_tuning as ph  # noqa: E402
from backend.app.services.replay_service import Edge, replay_records  # noqa: E402

EXP = ROOT / "docs" / "experiments"


def e(a, b, status="CANDIDATE_ASSOCIATION", sim=0.9, mt="PLAYBOOK"):
    return Edge(a, b, status, mt, (), 0.7, sim)


def test_observed_links_are_always_kept_and_candidates_need_the_threshold():
    edges = [e("a", "b", "OBSERVED_MATCH", None, "EXACT_IDENTIFIER"), e("c", "d", sim=0.78), e("e", "f", sim=0.92),
             e("g", "h", "DISPUTED_ASSOCIATION", 0.99)]
    assert ph.variant_edges(edges, 0.75, "components") == [("a", "b"), ("c", "d"), ("e", "f")]
    assert ph.variant_edges(edges, 0.85, "components") == [("a", "b"), ("e", "f")]
    assert ph.variant_edges(edges, 0.99, "components") == [("a", "b")]            # disputed links are never used


def test_triangle_clustering_cuts_a_bridge_but_keeps_a_supported_link():
    # a-b-c form a triangle; c-d is a bridge to a separate group d-e-f
    edges = [e("a", "b"), e("b", "c"), e("a", "c"), e("c", "d"), e("d", "e"), e("e", "f"), e("d", "f")]
    kept = set(ph.variant_edges(edges, 0.75, "triangle"))
    assert ("c", "d") not in kept
    assert {("a", "b"), ("b", "c"), ("a", "c"), ("d", "e"), ("e", "f"), ("d", "f")} <= kept
    comp = em.components(list("abcdef"), list(kept))
    assert comp["a"] == comp["c"] and comp["d"] == comp["f"] and comp["c"] != comp["d"]
    assert len(set(em.components(list("abcdef"), ph.variant_edges(edges, 0.75, "components")).values())) == 1


def test_unknown_clustering_is_rejected():
    with pytest.raises(ValueError):
        ph.variant_edges([], 0.75, "kmeans")


def test_a_higher_threshold_can_be_read_from_a_run_at_the_preregistered_one():
    """Candidate links of a pipeline run at T' equal the links with stored similarity >= T' of a run at 0.75."""
    records = gen.generate(900, 0.5)
    pick = [r for r in records if r["campaign_instance_id"] in ("T1-c1", "T2-c1", "T4-c1", "T5-c1")]
    pick += [r for r in records if r["campaign_template_id"] == "D3"][:3]
    base = replay_records(pick)
    for t in (0.85, 0.95):
        direct = replay_records(pick, t_candidate=t)
        direct_cands = {(x.a, x.b) for x in direct.edges if x.status == "CANDIDATE_ASSOCIATION"}
        derived = {(x.a, x.b) for x in base.edges if x.status == "CANDIDATE_ASSOCIATION" and (x.similarity or 0) >= t}
        assert direct_cands == derived, f"threshold {t}"
        assert {(x.a, x.b) for x in direct.edges if x.status == "OBSERVED_MATCH"} == \
               {(x.a, x.b) for x in base.edges if x.status == "OBSERVED_MATCH"}


def test_the_dev_and_fresh_seeds_are_new_and_do_not_overlap_anything_else():
    used = set(range(1001, 1011)) | {1, 900}
    assert not set(ph.DEV_SEEDS) & used and not set(ph.FRESH_SEEDS) & used
    assert not set(ph.DEV_SEEDS) & set(ph.FRESH_SEEDS) and len(ph.FRESH_SEEDS) >= 10


def test_committed_tuning_follows_the_protocol():
    tuning = json.loads((EXP / "posthoc_tuning.json").read_text(encoding="utf-8"))
    assert "POST-HOC" in tuning["notice"] and "unchanged" in tuning["notice"]
    assert tuning["protocol"]["data"].startswith("dev split only")
    assert tuning["protocol"]["seeds"] == ph.DEV_SEEDS and tuning["protocol"]["rotation_levels"] == ph.DEV_LEVELS
    best = max(tuning["table"], key=lambda r: (r["mean_f1_both_truths"], -r["mean_far_both_truths"], r["t_candidate"]))
    assert tuning["chosen"] == best                                          # the declared rule picked it
    assert {r["variant"] for r in tuning["table"]} == {ph.label(t, c) for t in ph.T_GRID for c in ph.CLUSTERINGS}
    head = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))   # the pre-registered headline is untouched
    assert head["design"]["t_candidate"] == 0.75 and len(head["runs"]) == 50
    assert tuning["artefact_sha256_lf"] == head["artefact_sha256_lf"]


def test_committed_fresh_results_use_the_variant_chosen_on_dev():
    fresh_file = EXP / "posthoc_fresh.json"
    tuning = json.loads((EXP / "posthoc_tuning.json").read_text(encoding="utf-8"))
    fresh = json.loads(fresh_file.read_text(encoding="utf-8"))
    assert "POST-HOC" in fresh["notice"]
    assert fresh["chosen_on_dev"] == tuning["chosen"]
    assert fresh["design"]["seeds"] == ph.FRESH_SEEDS and len(fresh["runs"]) == 50
    head = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))
    assert fresh["artefact_sha256_lf"] == head["artefact_sha256_lf"]


# ---------------------------------------------------------------------------------------------
# The production default stays at the pre-registered 0.75 and the headline results stay as they were
# ---------------------------------------------------------------------------------------------

HEADLINE_SHA256_LF = "36bd90a96e39e022152be80a9c97c00db63d4b55ad5bd2f4b5cce6e83cb7198e"


def test_production_default_threshold_is_still_the_preregistered_0_75():
    import inspect

    from ai_engine.fingerprint.similarity import DEFAULT_T_CANDIDATE
    from backend.app.core.config import settings

    assert DEFAULT_T_CANDIDATE == 0.75 and settings.T_CANDIDATE == 0.75
    default = inspect.signature(replay_records).parameters["t_candidate"].default
    assert default is None                                 # None = use the application's 0.75, never a tuned value


def test_a_tuned_threshold_in_a_replay_does_not_leak_into_the_settings():
    from backend.app.core.config import settings

    records = gen.generate(900, 0.5)
    pick = [r for r in records if r["campaign_instance_id"] in ("T1-c1",)]
    replay_records(pick, t_candidate=0.95)
    assert settings.T_CANDIDATE == 0.75                    # patched for that run only


def test_the_headline_results_file_is_exactly_what_the_experiment_produced():
    """docs/experiments/rotation.json holds the pre-registered E4 headline. The post-hoc work writes only its own
    files, so this hash must never change (a re-run of the experiment on purpose would update it, with a log entry)."""
    import evaluate_model

    assert evaluate_model.sha256_lf(EXP / "rotation.json") == HEADLINE_SHA256_LF
    assert ph.TUNING_FILE.name == "posthoc_tuning.json" and ph.FRESH_FILE.name == "posthoc_fresh.json"
    assert {ph.TUNING_FILE.name, ph.FRESH_FILE.name}.isdisjoint({"rotation.json", "rotation_all.png", "rotation_test.png"})
