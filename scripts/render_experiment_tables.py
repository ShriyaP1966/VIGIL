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
README = ROOT / "README.md"
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


def posthoc_fresh_tables() -> str:
    d = json.loads((EXP / "posthoc_fresh.json").read_text(encoding="utf-8"))
    arms = ["A", "B", "C", "D", "D_tuned"]
    names = {"D": "D (pre-reg.)", "D_tuned": "D post-hoc"}
    head = lambda suffix: [f"{names.get(a, a)} {suffix}" for a in arms]   # noqa: E731
    out = [f"Fresh seeds {d['design']['seeds'][0]}-{d['design']['seeds'][-1]}, mean ± sample std over {len(d['design']['seeds'])} seeds. "
           f"Column **D post-hoc** is variant `{d['chosen_on_dev']['variant']}`, chosen on dev data after the pre-registered "
           "results were seen. Column **D (pre-reg.)** is the pre-registered arm D, re-measured on the same runs.\n"]
    for sl, title in (("all", "all 150 incidents"), ("test", "test-split incidents only (secondary)")):
        for g, gt in TRUTH.items():
            agg = d["aggregate"][sl][g]
            levels = sorted(agg, key=float)
            out.append(f"**{title}, ground truth {gt}**\n")
            out.append(table(["r"] + head("F1"), [[lv] + [cell(agg[lv][a]["f1"]) for a in arms] for lv in levels]))
            out.append("")
            out.append(table(["r"] + head("FAR"), [[lv] + [cell(agg[lv][a]["far"], 4) for a in arms] for lv in levels]))
            out.append("")
            if sl == "all":
                out.append(table(["r", "D pre-reg. P / R", "D post-hoc P / R"],
                                 [[lv] + [f"{cell(agg[lv][a]['precision'], 2)} / {cell(agg[lv][a]['recall'], 2)}"
                                          for a in ("D", "D_tuned")] for lv in levels]))
                out.append("")
    sizes: dict[float, list] = {}
    for r in d["largest_component_by_run"]:
        sizes.setdefault(r["rotation"], []).append((r["d_preregistered"], r["d_tuned"]))
    out.append("Largest predicted group (mean incidents over seeds; 150 incidents per run):\n")
    out.append(table(["r", "D pre-reg.", "D post-hoc"],
                     [[str(lv), f"{sum(a for a, _ in v) / len(v):.1f}", f"{sum(b for _, b in v) / len(v):.1f}"]
                      for lv, v in sorted(sizes.items())]))
    dec = d["decoys_linked_tuned_pooled"]
    names_d = {"similar_wording_different_origin": "D1 similar wording, different origin",
               "benign_shared_identifier": "D2 shared identifier, benign context",
               "incompatible_chronology": "D3 same tactics, incompatible chronology",
               "ambiguous_extraction": "D4 ambiguous extraction"}
    out.append("\nDecoys linked by the post-hoc variant (pooled over the 50 runs; the pre-registered arm D linked D1 100 and "
               "D3 185 of 250 in the headline runs, a different set of seeds):\n")
    out.append(table(["decoy type", "linked", "of"],
                     [[names_d[k], str(v["linked"]), str(v["total"])] for k, v in sorted(dec.items(), key=lambda kv: names_d[kv[0]])]))
    return "\n".join(out)


def heldout_table() -> str:
    d = json.loads((EXP / "heldout.json").read_text(encoding="utf-8"))
    s = d["metrics"]["scenario_level"]
    ps = d["per_scenario"]
    by_type: dict[str, list[int]] = {}
    for p in ps:
        if not p["is_legitimate"]:
            c = by_type.setdefault(p["type"] or "unspecified", [0, 0])
            c[1] += 1
            c[0] += p["scam_tactic_detected"]
    missed = [p["id"] for p in ps if not p["is_legitimate"] and not p["scam_tactic_detected"]]
    false_alarms = [p["id"] for p in ps if p["is_legitimate"] and p["scam_tactic_detected"]]
    rows = [["Scam scenarios with at least one scam tactic detected", f"{s['scam_scenarios_detected']} of {s['scam_scenarios']}",
             f"{s['scam_detection_rate']}"],
            ["Legitimate scenarios falsely flagged as a scam", f"{s['legitimate_false_alarms']} of {s['legitimate_scenarios']}",
             f"{s['legitimate_false_alarm_rate']}"]]
    out = [table(["scenario-level measure", "count", "rate"], rows), "",
           f"Missed scam scenarios: {', '.join(missed) if missed else 'none'}. "
           f"Falsely flagged legitimate scenarios: {', '.join(false_alarms) if false_alarms else 'none'}.", "",
           "Scam scenarios detected, by the owner's scenario type:", "",
           table(["type", "detected"], [[k, f"{a} of {b}"] for k, (a, b) in sorted(by_type.items())]), "",
           f"Tactic-level scores: **{d['metrics']['tactic_level']}**. Extractor `{d['extractor']['name']}@"
           f"{d['extractor']['version'].split('@')[-1]}`, lexicon sha256 `{d['extractor']['lexicon_sha256'][:16]}…` "
           "(the frozen pre-registered lexicon)."]
    return "\n".join(out)


SECTIONS = {
    "heldout": heldout_table,
    "posthoc-tune": posthoc_tune_table,
    "posthoc-fresh": posthoc_fresh_tables,
    "rotation-all": lambda: rotation_tables("all"),
    "rotation-test": lambda: rotation_tables("test"),
    "candidates": candidate_table,
    "tau": tau_table,
    "e3": e3_tables,
    "tactics": tactics_table,
    "entities": entities_table,
    "latency": latency_table,
}


def _f1far(c: dict) -> str:
    f, a = c["f1"]["mean"], c["far"]["mean"]
    return "n/a" if f is None else f"{f:.2f} / {a:.3f}"


def readme_headline() -> str:
    """Compact pre-registered headline for the README: F1 / false association rate, all 150 incidents, 10 seeds."""
    agg = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))["aggregate"]["all"]
    out = []
    for g, title in TRUTH.items():
        out.append(f"**Ground truth {title}**; cells are pairwise F1 / false association rate:\n")
        out.append(table(["rotation r"] + [f"{a}" for a in ARMS],
                         [[lv] + [_f1far(agg[g][lv][a]) for a in ARMS] for lv in ("0.0", "0.5", "1.0")]))
        out.append("")
    return "\n".join(out).rstrip()


def readme_posthoc() -> str:
    """Post-hoc row for the README: the pre-registered arm D next to the dev-tuned variant on fresh seeds."""
    d = json.loads((EXP / "posthoc_fresh.json").read_text(encoding="utf-8"))
    agg = d["aggregate"]["all"]
    out = []
    for g, title in TRUTH.items():
        out.append(f"**{title}** (fresh seeds, F1 / false association rate):\n")
        out.append(table(["rotation r", "D, pre-registered (T=0.75)", f"D, post-hoc ({d['chosen_on_dev']['variant']})"],
                         [[lv, _f1far(agg[g][lv]["D"]), _f1far(agg[g][lv]["D_tuned"])] for lv in ("0.0", "0.5", "1.0")]))
        out.append("")
    return "\n".join(out).rstrip()


def readme_heldout() -> str:
    d = json.loads((EXP / "heldout.json").read_text(encoding="utf-8"))
    s = d["metrics"]["scenario_level"]
    ps = d["per_scenario"]
    missed = ", ".join(p["id"] for p in ps if not p["is_legitimate"] and not p["scam_tactic_detected"]) or "none"
    flagged = ", ".join(p["id"] for p in ps if p["is_legitimate"] and p["scam_tactic_detected"]) or "none"
    return table(["held-out measure (run once)", "result", "which"], [
        ["Scam scenarios with a scam tactic detected", f"{s['scam_scenarios_detected']} of {s['scam_scenarios']}", f"missed: {missed}"],
        ["Legitimate scenarios flagged as scams (false alarms)", f"{s['legitimate_false_alarms']} of {s['legitimate_scenarios']}", f"flagged: {flagged}"],
        ["Tactic-level scores", "not measured", "no per-utterance labels in the set"]])


def readme_key_results() -> str:
    """Five lines for the top of the README, every number read from the result files."""
    rot = json.loads((EXP / "rotation.json").read_text(encoding="utf-8"))["aggregate"]["all"]
    post = json.loads((EXP / "posthoc_fresh.json").read_text(encoding="utf-8"))["aggregate"]["all"]
    held = json.loads((EXP / "heldout.json").read_text(encoding="utf-8"))
    s, ps = held["metrics"]["scenario_level"], held["per_scenario"]
    missed = ", ".join(p["id"] for p in ps if not p["is_legitimate"] and not p["scam_tactic_detected"])
    flagged = " and ".join(p["id"] for p in ps if p["is_legitimate"] and p["scam_tactic_detected"])

    def v(src: dict, g: str, lv: str, arm: str, k: str) -> float:
        return src[g][lv][arm][k]["mean"]

    return "\n".join([
        f"* **Pre-registered: rotating identifiers breaks identifier linking.** Under the campaign-instance truth, the identifier "
        f"graph (B) and B with counter-evidence (C) fall from F1 {v(rot, 'a', '0.0', 'B', 'f1'):.2f} and {v(rot, 'a', '0.0', 'C', 'f1'):.2f} "
        f"with no rotation to {v(rot, 'a', '1.0', 'B', 'f1'):.2f} and {v(rot, 'a', '1.0', 'C', 'f1'):.2f} when every identifier is replaced.",
        f"* **Counter-evidence raises precision at no cost in recall:** with no rotation, precision {v(rot, 'a', '0.0', 'C', 'precision'):.2f} for C "
        f"against {v(rot, 'a', '0.0', 'B', 'precision'):.2f} for B.",
        f"* **The playbook fingerprint (D) recovers links that rotation hides, but over-merges.** At r = 0.5 its F1 is "
        f"{v(rot, 'a', '0.5', 'D', 'f1'):.2f} under the instance truth (the plain text baseline A scores {v(rot, 'a', '0.5', 'A', 'f1'):.2f}) and "
        f"{v(rot, 'b', '0.5', 'D', 'f1'):.2f} under the script-family truth, with a false association rate of {v(rot, 'b', '0.5', 'D', 'far'):.2f}.",
        f"* **Post-hoc, tuned after seeing those results (fresh seeds, reported separately):** a higher threshold lifts D to F1 "
        f"{v(post, 'b', '0.5', 'D_tuned', 'f1'):.2f} with a false association rate of {v(post, 'b', '0.5', 'D_tuned', 'far'):.3f} under the "
        f"script-family truth (from {v(post, 'b', '0.5', 'D', 'f1'):.2f} and {v(post, 'b', '0.5', 'D', 'far'):.3f}), but only "
        f"{v(post, 'a', '0.5', 'D_tuned', 'f1'):.2f} under the instance truth. The headline and the application default (`T_CANDIDATE = 0.75`) are unchanged.",
        f"* **Held-out set, run once:** {s['scam_scenarios_detected']} of {s['scam_scenarios']} scam scenarios had a scam tactic detected "
        f"(missed: {missed}, a cut-off call), but **{s['legitimate_false_alarms']} of {s['legitimate_scenarios']} legitimate scenarios "
        f"({flagged}) were flagged as scams, a false-alarm rate of {s['legitimate_false_alarms']} of {s['legitimate_scenarios']}.** "
        "Tactic-level scores were not measured. Small, synthetic set.",
    ])


README_SECTIONS = {
    "readme-keyresults": readme_key_results,
    "readme-headline": readme_headline,
    "readme-posthoc": readme_posthoc,
    "readme-heldout": readme_heldout,
}


def render(text: str, sections: dict | None = None) -> str:
    for name, fn in (sections or SECTIONS).items():
        pattern = re.compile(rf"<!-- BEGIN:{name} -->.*?<!-- END:{name} -->", re.S)
        if not pattern.search(text):
            raise SystemExit(f"marker {name!r} not found")
        block = f"<!-- BEGIN:{name} -->\n{fn()}\n<!-- END:{name} -->"
        text = pattern.sub(lambda _m: block, text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stale = False
    for path, sections in ((DOC, None), (README, README_SECTIONS)):
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        new = render(current, sections)
        if args.check:
            if new != current:
                print(f"{path.relative_to(ROOT)} is out of date: run python scripts/render_experiment_tables.py")
                stale = True
        else:
            path.write_text(new, encoding="utf-8", newline="\n")
            print(f"Updated {path.relative_to(ROOT)}")
    if args.check:
        if not stale:
            print("docs/EXPERIMENTS.md and README.md tables match docs/experiments/*.json")
        return 1 if stale else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
