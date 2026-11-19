#!/usr/bin/env python3
"""Fills the generated tables of docs/EXPERIMENTS.md from docs/experiments/*.json, so no number in a table is typed
by hand. Tables sit between `<!-- BEGIN:name -->` and `<!-- END:name -->` markers.

  python scripts/render_experiment_tables.py           rewrite the tables in place
  python scripts/render_experiment_tables.py --check   exit 1 if the document is out of date (used by a test)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "EXPERIMENTS.md"
EXP = ROOT / "docs" / "experiments"
ARMS = ["A", "B", "C", "D"]
TRUTH = {"a": "(a) same campaign instance", "b": "(b) same script family"}


def cell(c: dict, digits: int = 3) -> str:
    if c["mean"] is None:
        return "n/a"
    s = f"{c['mean']:.{digits}f}"
    return s + (f" ± {c['std']:.{digits}f}" if c["std"] is not None else "")


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] + ["---:"] * (len(header) - 1)) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def rotation_tables(slice_name: str) -> str:
    d = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))["aggregate"][slice_name]
    out = []
    for g, title in TRUTH.items():
        levels = sorted(d[g], key=float)
        out.append(f"**Ground truth {title}**\n")
        out.append("Pairwise F1, mean ± sample std over seeds:\n")
        out.append(table(["r"] + [f"{a} F1" for a in ARMS],
                         [[lv] + [cell(d[g][lv][a]["f1"]) for a in ARMS] for lv in levels]))
        out.append("\nFalse association rate (share of non-pairs placed in one predicted campaign):\n")
        out.append(table(["r"] + [f"{a} FAR" for a in ARMS],
                         [[lv] + [cell(d[g][lv][a]["far"], 4) for a in ARMS] for lv in levels]))
        out.append("\nPairwise precision / recall:\n")
        out.append(table(["r"] + [f"{a} P / R" for a in ARMS],
                         [[lv] + [f"{cell(d[g][lv][a]['precision'], 2)} / {cell(d[g][lv][a]['recall'], 2)}"
                                  for a in ARMS] for lv in levels]))
        out.append("")
    return "\n".join(out)


def candidate_table() -> str:
    d = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))["aggregate"]["all"]
    rows = []
    for g in ("a", "b"):
        for lv in sorted(d[g], key=float):
            c = d[g][lv]["D"]
            rows.append([TRUTH[g], lv, cell(c["candidate_precision"], 3), cell(c["candidate_recall"], 3),
                         str(c["candidate_recall"]["n"])])
    return table(["ground truth", "r", "candidate precision (edges)", "candidate recall (pairs C misses)",
                  "seeds with a defined recall"], rows)


def tau_table() -> str:
    cal = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))["calibration_tau_a"]
    rows = [[f"{r['tau']:.2f}", f"{r['precision']}" if r["precision"] is not None else "n/a",
             f"{r['recall']}" if r["recall"] is not None else "n/a", f"{r['f1']}"] for r in cal["table"]]
    return (table(["tau_A", "precision", "recall", "F1 (truth a)"], rows)
            + f"\n\nChosen tau_A = **{cal['chosen_tau_a']}** (seed {cal['seed']}, r = {cal['rotation']}, "
              f"dev split only, {cal['incidents']} incidents).")


def e3_tables() -> str:
    pooled = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))["integrity_pooled"]
    sample = json.loads((EXP / "associations.json").read_text(encoding="utf-8"))["integrity"]

    def counters(i: dict) -> list[list[str]]:
        return [
            ["I1 violations (OBSERVED_MATCH without exactly equal identifiers); required 0", str(i["i1_violations"])],
            ["Identifier links touching a negative or decoy, before counter-evidence (arm B level)",
             str(i["identifier_edges_touching_benign_before_counter_evidence"])],
            ["Observed links touching a negative or decoy, after counter-evidence (arm C level)",
             str(i["observed_edges_touching_benign_after_counter_evidence"])],
            ["Candidate links touching a negative or decoy (arm D)", str(i["candidate_edges_touching_benign"])],
            ["Negatives with an observed link", f"{i['negatives_with_observed_edge']} of {i['negatives_total']}"],
            ["Negatives with an observed or candidate link",
             f"{i['negatives_with_observed_or_candidate_edge']} of {i['negatives_total']}"],
            ["Campaign hypotheses that contain a negative or a decoy",
             f"{i['campaign_hypotheses_containing_a_negative_or_decoy']} of {i['campaign_hypotheses']}"],
        ]

    def decoys(i: dict) -> list[list[str]]:
        names = {"similar_wording_different_origin": "D1 similar wording, different origin",
                 "benign_shared_identifier": "D2 shared identifier, benign context",
                 "incompatible_chronology": "D3 same tactics, incompatible chronology",
                 "ambiguous_extraction": "D4 ambiguous extraction"}
        return [[names[k], f"{v['linked_observed']} of {v['total']}", f"{v['linked_observed_or_candidate']} of {v['total']}"]
                for k, v in sorted(i["decoys"].items(), key=lambda kv: names[kv[0]])]

    return "\n".join([
        "**Committed sample** (`data/scenarios.jsonl`, 150 incidents):\n",
        table(["counter", "value"], counters(sample)), "",
        table(["decoy type", "linked by an observed link", "linked by an observed or candidate link"], decoys(sample)), "",
        f"**Pooled over all {pooled['runs']} E4 runs** (10 seeds x 5 rotation levels; 2000 negatives, 1000 decoys):\n",
        table(["counter", "value"], counters(pooled)), "",
        table(["decoy type", "linked by an observed link", "linked by an observed or candidate link"], decoys(pooled)),
    ])


def tactics_table() -> str:
    rows = []
    for split in ("train", "dev", "test"):
        m = json.loads((EXP / f"tactics_{split}.json").read_text(encoding="utf-8"))["metrics"]
        rows.append([split, str(m["macro_f1_over_labels_with_support"]), str(m["micro"]["precision"]),
                     str(m["micro"]["recall"]), str(m["incident_stage_sequence_exact_match"]),
                     f"{m['decoy_utterances_labelled_despite_no_gold_label']['of_which_labelled_by_extractor']}/"
                     f"{m['decoy_utterances_labelled_despite_no_gold_label']['utterances_without_gold_labels']}"])
    return table(["split", "macro-F1", "micro P", "micro R", "stage sequence exact", "decoy notices labelled as scam"], rows)


def entities_table() -> str:
    m = json.loads((EXP / "entities_all.json").read_text(encoding="utf-8"))["metrics"]
    return table(["type", "tp", "fp", "fn", "P", "R", "F1"],
                 [[t, str(v["tp"]), str(v["fp"]), str(v["fn"]), str(v["precision"]), str(v["recall"]), str(v["f1"])]
                  for t, v in m.items()])


def latency_table() -> str:
    d = json.loads((EXP / "latency.json").read_text(encoding="utf-8"))
    rows = [[k, str(v["mean_ms"]), str(v["median_ms"]), str(v["p95_ms"]), str(v["max_ms"])]
            for k, v in {**d["stages_ms"], "end to end (create + analyse)": d["end_to_end_ms"]}.items()]
    e = d["end_to_end_ms"]
    return (table(["stage", "mean ms", "median ms", "p95 ms", "max ms"], rows)
            + f"\n\nEnd to end, first 20 incidents: mean {e['first_20_mean_ms']} ms; last 20: mean {e['last_20_mean_ms']} ms.")


def posthoc_tune_table() -> str:
    d = json.loads((EXP / "posthoc_tuning.json").read_text(encoding="utf-8"))
    rows = [[r["variant"], f"{r['mean_f1_both_truths']:.4f}", f"{r['mean_far_both_truths']:.4f}",
             f"{r['f1_a']:.4f}", f"{r['f1_b']:.4f}"] for r in d["table"]]
    c, b = d["chosen"], d["baseline"]
    return (table(["variant (dev data only)", "mean F1, both truths", "mean false association rate", "F1 (a)", "F1 (b)"], rows)
            + f"\n\nChosen on dev data by the declared rule: **{c['variant']}** (mean F1 {c['mean_f1_both_truths']:.4f}, "
              f"against {b['mean_f1_both_truths']:.4f} for the pre-registered {b['variant']}).")


SECTIONS = {
    "posthoc-tune": posthoc_tune_table,
    "rotation-all": lambda: rotation_tables("all"),
    "rotation-test": lambda: rotation_tables("test"),
    "candidates": candidate_table,
    "tau": tau_table,
    "e3": e3_tables,
    "tactics": tactics_table,
    "entities": entities_table,
    "latency": latency_table,
}


def render(text: str) -> str:
    for name, fn in SECTIONS.items():
        pattern = re.compile(rf"<!-- BEGIN:{name} -->.*?<!-- END:{name} -->", re.S)
        if not pattern.search(text):
            raise SystemExit(f"marker {name!r} not found in {DOC.name}")
        block = f"<!-- BEGIN:{name} -->\n{fn()}\n<!-- END:{name} -->"
        text = pattern.sub(lambda _m: block, text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    current = DOC.read_text(encoding="utf-8")
    new = render(current.replace("\r\n", "\n"))
    if args.check:
        if new != current.replace("\r\n", "\n"):
            print("docs/EXPERIMENTS.md is out of date: run python scripts/render_experiment_tables.py")
            return 1
        print("docs/EXPERIMENTS.md tables match docs/experiments/*.json")
        return 0
    DOC.write_text(new, encoding="utf-8", newline="\n")
    print(f"Updated {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
