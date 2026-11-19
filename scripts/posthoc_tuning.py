#!/usr/bin/env python3
"""POST-HOC, EXPLORATORY: a tuned fingerprint threshold and clustering for arm D (docs/EXPERIMENTS.md section 10).

This was added AFTER the pre-registered E4 results (docs/experiments/rotation.json) were seen, because they showed
that arm D over-merges. It never changes, replaces or overwrites those headline results (T_candidate = 0.75, plain
connected components); it writes its own files and every table that quotes it is labelled post-hoc.

Protocol (committed before the fresh-seed stage was run):
  stage "tune"   DEV DATA ONLY. Seeds 901-905, rotation 0 / 0.5 / 1.0, pipeline at the pre-registered T = 0.75, scored on
                 the `dev` split only (T2, T5, N3, N4, D2). Variants = T_candidate in {0.75, 0.80, 0.85, 0.90, 0.95} x
                 clustering in {components, triangle}. Criterion: the highest mean pairwise F1 over both ground truths
                 (a) and (b), the three rotation levels and the five seeds; ties go to the lower mean false association
                 rate, then the higher threshold. The `test` split is not scored here; neither is the held-out set.
  stage "fresh"  The chosen variant is evaluated on FRESH seeds 2001-2010 (never used before), all five rotation
                 levels, next to arms A, B, C and the pre-registered arm D, on the same runs.

Raising the threshold is read from a run made at 0.75: a candidate link exists at T' >= 0.75 exactly when its stored
playbook similarity is >= T' (tests/test_posthoc_tuning.py checks this against a pipeline run at T').
Clustering "triangle" keeps a candidate link only if its two incidents also share a neighbour in the link graph, which
cuts links that merely bridge two groups; observed links are always kept.

  python scripts/posthoc_tuning.py --stage tune
  python scripts/posthoc_tuning.py --stage fresh
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import eval_metrics as em  # noqa: E402
import evaluate_model as ev  # noqa: E402

DEV_SEEDS = [901, 902, 903, 904, 905]
DEV_LEVELS = [0.0, 0.5, 1.0]
FRESH_SEEDS = [2001 + i for i in range(10)]
T_GRID = [0.75, 0.80, 0.85, 0.90, 0.95]
CLUSTERINGS = ["components", "triangle"]
EXP = ROOT / "docs" / "experiments"
TUNING_FILE = EXP / "posthoc_tuning.json"
FRESH_FILE = EXP / "posthoc_fresh.json"
NOTICE = ("POST-HOC and exploratory: chosen after the pre-registered results were seen, on dev data. The headline "
          "results in rotation.json (T_candidate 0.75, plain connected components) are unchanged.")


def variant_edges(edges, t: float, clustering: str) -> list[tuple[str, str]]:
    """Edges of arm D under a variant: observed links, plus candidate links with similarity >= t (and, for
    'triangle', supported by a shared neighbour)."""
    observed = [(e.a, e.b) for e in edges if e.status == "OBSERVED_MATCH"]
    cands = [(e.a, e.b) for e in edges
             if e.status == "CANDIDATE_ASSOCIATION" and (e.similarity or 0.0) >= t - 1e-12]
    if clustering == "components":
        return observed + cands
    if clustering != "triangle":
        raise ValueError(clustering)
    neighbours: dict[str, set[str]] = defaultdict(set)
    for a, b in observed + cands:
        neighbours[a].add(b)
        neighbours[b].add(a)
    kept = [(a, b) for a, b in cands if (neighbours[a] & neighbours[b]) - {a, b}]
    return observed + kept


def label(t: float, clustering: str) -> str:
    return f"T={t:.2f}/{clustering}"


# ---------------------------------------------------------------------------------------------
# stage 1: tune on dev data only
# ---------------------------------------------------------------------------------------------

def _tune_job(job: tuple[int, float]) -> dict:
    seed, rotation = job
    from generate_dataset import generate
    from backend.app.services.replay_service import replay_records
    records = generate(seed, rotation)
    result = replay_records(records)
    dev = [r for r in records if r["split"] == "dev"]
    dev_ids = [r["incident_id"] for r in dev]
    truths, benign = em.truth_functions(dev), em.benign_ids(dev)
    out = {}
    for t in T_GRID:
        for clustering in CLUSTERINGS:
            comp = em.components(dev_ids, variant_edges(result.edges, t, clustering))
            out[label(t, clustering)] = {
                g: {k: v for k, v in em.pairwise(dev_ids, comp, truths[g], benign).items() if k in ("f1", "far")}
                for g in ("a", "b")}
    return {"seed": seed, "rotation": rotation, "variants": out}


def stage_tune(workers: int) -> dict:
    from concurrent.futures import ProcessPoolExecutor
    jobs = [(s, r) for r in DEV_LEVELS for s in DEV_SEEDS]
    print(f"tuning on dev data only: {len(jobs)} runs on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        runs = list(pool.map(_tune_job, jobs))
    table = []
    for t in T_GRID:
        for clustering in CLUSTERINGS:
            key = label(t, clustering)
            f1 = [r["variants"][key][g]["f1"] for r in runs for g in ("a", "b")]
            far = [r["variants"][key][g]["far"] for r in runs for g in ("a", "b")]
            table.append({"variant": key, "t_candidate": t, "clustering": clustering,
                          "mean_f1_both_truths": round(sum(x or 0.0 for x in f1) / len(f1), 4),
                          "mean_far_both_truths": round(sum(x or 0.0 for x in far) / len(far), 4),
                          "f1_a": round(sum(r["variants"][key]["a"]["f1"] or 0.0 for r in runs) / len(runs), 4),
                          "f1_b": round(sum(r["variants"][key]["b"]["f1"] or 0.0 for r in runs) / len(runs), 4)})
    best = max(table, key=lambda row: (row["mean_f1_both_truths"], -row["mean_far_both_truths"], row["t_candidate"]))
    return {
        "stage": "tune", "notice": NOTICE,
        "command": "python scripts/posthoc_tuning.py --stage tune",
        "protocol": {"data": "dev split only (T2, T5, N3, N4, D2)", "seeds": DEV_SEEDS, "rotation_levels": DEV_LEVELS,
                     "criterion": "highest mean pairwise F1 over truths (a) and (b), levels and seeds; ties: lower mean "
                                  "false association rate, then higher threshold",
                     "grid": {"t_candidate": T_GRID, "clustering": CLUSTERINGS},
                     "not_used": "the test split, seeds 1001-1010, seed 900 and the held-out set"},
        "table": table, "chosen": best,
        "baseline": next(r for r in table if r["variant"] == label(0.75, "components")),
        "artefact_sha256_lf": {p: ev.sha256_lf(ROOT / p) for p in ev.HASHED},
        "environment": ev.environment(),
    }


# ---------------------------------------------------------------------------------------------
# stage 2: fresh seeds
# ---------------------------------------------------------------------------------------------

def _fresh_job(job: tuple[int, float, float, str, float]) -> dict:
    seed, rotation, t, clustering, tau_a = job
    from generate_dataset import generate
    from backend.app.services.replay_service import replay_records
    records = generate(seed, rotation)
    result = replay_records(records)
    ids = [r["incident_id"] for r in records]
    sets = ev.arm_edge_sets(records, result.edges, tau_a)          # A, B, C, D (pre-registered definitions)
    sets["D_tuned"] = variant_edges(result.edges, t, clustering)
    comps = {arm: em.components(ids, e) for arm, e in sets.items()}
    truths, benign = em.truth_functions(records), em.benign_ids(records)
    slices = {"all": ids, "test": [r["incident_id"] for r in records if r["split"] == "test"]}
    scores: dict = {}
    for sl, scored in slices.items():
        scores[sl] = {}
        for g in ("a", "b"):
            scores[sl][g] = {arm: {k: ev.rnd(v) if isinstance(v, float) else v
                                   for k, v in em.pairwise(scored, comps[arm], truths[g], benign).items()}
                             for arm in comps}
    linked = {i for e in sets["D_tuned"] for i in e}
    decoys: dict[str, dict] = {}
    for r in records:
        if r["scenario_type"] == "decoy":
            d = decoys.setdefault(r["decoy_type"], {"total": 0, "linked": 0})
            d["total"] += 1
            d["linked"] += r["incident_id"] in linked
    sizes = sorted(Counter(comps["D_tuned"].values()).values(), reverse=True)
    sizes0 = sorted(Counter(comps["D"].values()).values(), reverse=True)
    return {"seed": seed, "rotation": rotation, "scores": scores, "decoys_linked_tuned": decoys,
            "largest_component": {"d_preregistered": sizes0[0], "d_tuned": sizes[0]}}


def stage_fresh(workers: int) -> dict:
    from concurrent.futures import ProcessPoolExecutor
    if not TUNING_FILE.exists():
        raise SystemExit("run --stage tune first (the fresh stage uses the variant chosen on dev data)")
    tuning = json.loads(TUNING_FILE.read_text(encoding="utf-8"))
    chosen = tuning["chosen"]
    cal = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))["calibration_tau_a"]["chosen_tau_a"]
    jobs = [(s, r, chosen["t_candidate"], chosen["clustering"], cal) for r in ev.ROTATION_LEVELS for s in FRESH_SEEDS]
    print(f"fresh seeds {FRESH_SEEDS[0]}-{FRESH_SEEDS[-1]}, variant {chosen['variant']}: {len(jobs)} runs on {workers} workers",
          flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        runs = list(pool.map(_fresh_job, jobs))
    arms = ["A", "B", "C", "D", "D_tuned"]
    agg: dict = {}
    for sl in ("all", "test"):
        agg[sl] = {}
        for g in ("a", "b"):
            agg[sl][g] = {}
            for level in ev.ROTATION_LEVELS:
                at = [r for r in runs if r["rotation"] == level]
                agg[sl][g][str(level)] = {
                    arm: {m: em.mean_std([r["scores"][sl][g][arm][m] for r in at])
                          for m in ("precision", "recall", "f1", "far", "far_benign")} for arm in arms}
    decoys: dict[str, Counter] = {}
    for r in runs:
        for name, d in r["decoys_linked_tuned"].items():
            decoys.setdefault(name, Counter()).update(d)
    return {
        "stage": "fresh", "notice": NOTICE, "command": "python scripts/posthoc_tuning.py --stage fresh",
        "chosen_on_dev": chosen, "baseline_on_dev": tuning["baseline"],
        "design": {"seeds": FRESH_SEEDS, "rotation_levels": ev.ROTATION_LEVELS, "tau_a": cal,
                   "std": "sample standard deviation (n - 1) over seeds",
                   "arms": {"D": "pre-registered arm D (T = 0.75, plain components), re-measured on these seeds",
                            "D_tuned": f"post-hoc variant {chosen['variant']}"}},
        "aggregate": agg,
        "decoys_linked_tuned_pooled": {k: dict(v) for k, v in sorted(decoys.items())},
        "largest_component_by_run": [{"seed": r["seed"], "rotation": r["rotation"], **r["largest_component"]} for r in runs],
        "runs": runs,
        "artefact_sha256_lf": {p: ev.sha256_lf(ROOT / p) for p in ev.HASHED},
        "caveat": ("Tuned after seeing the pre-registered results, on dev data, and evaluated on fresh seeds of the same "
                   "generator. Synthetic data; no claim about real traffic."),
        "environment": ev.environment(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["tune", "fresh"])
    ap.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 2)))
    args = ap.parse_args()
    if args.stage == "tune":
        result = stage_tune(args.workers)
        EXP.mkdir(parents=True, exist_ok=True)
        TUNING_FILE.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(f"chosen on dev data: {result['chosen']['variant']}  (baseline {result['baseline']['mean_f1_both_truths']} "
              f"-> {result['chosen']['mean_f1_both_truths']} mean F1)")
        for row in result["table"]:
            print(f"  {row['variant']:24} F1 {row['mean_f1_both_truths']:.4f}  FAR {row['mean_far_both_truths']:.4f}")
    else:
        result = stage_fresh(args.workers)
        FRESH_FILE.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        for g in ("a", "b"):
            print(f"\nfresh seeds, all incidents, truth ({g}): F1 / FAR")
            for level, arms in result["aggregate"]["all"][g].items():
                cells = " ".join(f"{a}:{(arms[a]['f1']['mean'] or 0):.3f}/{(arms[a]['far']['mean'] or 0):.3f}"
                                 for a in ("A", "B", "C", "D", "D_tuned"))
                print(f"  r={level:>4}  {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
