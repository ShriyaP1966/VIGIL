#!/usr/bin/env python3
"""Draws the rotation-experiment chart from docs/experiments/rotation.json (blueprint §8.3). Nothing is typed in:
every plotted number is read from that file, which evaluate_model.py wrote.

  python scripts/plot_results.py [--slice all|test] [--out docs/experiments/rotation_all.png]

matplotlib is a dev-only dependency (scripts/requirements-dev.txt); the app does not need it.
Two ground truths side by side: left (a) same campaign instance, right (b) same script family.
Top row pairwise F1, bottom row false association rate. Error bars are sample standard deviations over seeds.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULT = ROOT / "docs" / "experiments" / "rotation.json"
MAX_BYTES = 200_000

# Okabe-Ito colour-blind-safe palette; marker and line style differ too, so colour is never the only cue
STYLE = {
    "A": dict(color="#555555", marker="o", ls=":", label="A  text similarity (TF-IDF)"),
    "B": dict(color="#0072B2", marker="s", ls="--", label="B  identifier graph"),
    "C": dict(color="#D55E00", marker="^", ls="-.", label="C  B + counter-evidence"),
    "D": dict(color="#009E73", marker="D", ls="-", label="D  C + playbook fingerprint"),
}
TRUTH_TITLE = {"a": "Ground truth (a): same campaign instance", "b": "Ground truth (b): same script family"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", default="all", choices=["all", "test"])
    ap.add_argument("--in", dest="inp", type=Path, default=RESULT)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = json.loads(args.inp.read_text(encoding="utf-8"))
    agg = data["aggregate"][args.slice]
    levels = sorted(float(k) for k in agg["a"])
    n_seeds = len(data["design"]["seeds"])
    scored = "all 150 incidents" if args.slice == "all" else "test-split incidents only"

    fig, axes = plt.subplots(2, 2, figsize=(10, 7.2), sharex=True)
    for col, g in enumerate(("a", "b")):
        for row, (metric, ylabel) in enumerate((("f1", "Pairwise F1"), ("far", "False association rate"))):
            ax = axes[row][col]
            for arm, st in STYLE.items():
                xs, ys, es = [], [], []
                for lv in levels:
                    cell = agg[g][str(lv)][arm][metric]
                    if cell["mean"] is not None:
                        xs.append(lv)
                        ys.append(cell["mean"])
                        es.append(cell["std"] or 0.0)
                ax.errorbar(xs, ys, yerr=es, color=st["color"], marker=st["marker"], ls=st["ls"], lw=1.8,
                            ms=6, capsize=3, label=st["label"])
            ax.set_ylim(-0.02, 1.02 if metric == "f1" else None)
            if metric == "far":
                ax.set_ylim(bottom=-0.002)
            ax.set_xticks(levels)
            ax.grid(alpha=0.25)
            if col == 0:
                ax.set_ylabel(ylabel)
            if row == 0:
                ax.set_title(TRUTH_TITLE[g], fontsize=10.5)
            if row == 1:
                ax.set_xlabel("Identifier rotation r (0 = never replaced, 1 = always replaced)")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, 0.06))
    fig.suptitle(f"Identifier-rotation experiment: synthetic data, {n_seeds} seeds, mean ± sample std, {scored}",
                 fontsize=11.5)
    fig.text(0.5, 0.005,
             "Arm D recognises a script family / playbook. Under (a) its precision is expected to be low: different "
             "instances of one template run an identical script.\nAll data synthetic; results do not imply real-world "
             "performance. Source: docs/experiments/rotation.json",
             ha="center", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.12, 1, 0.97))

    out = args.out or ROOT / "docs" / "experiments" / f"rotation_{args.slice}.png"
    fig.savefig(out, dpi=110)
    size = out.stat().st_size
    print(f"Wrote {out.relative_to(ROOT)} ({size} bytes)")
    if size > MAX_BYTES:
        print(f"Chart is over the {MAX_BYTES} byte budget")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
