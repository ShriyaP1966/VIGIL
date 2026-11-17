#!/usr/bin/env python3
"""Read-only diagnostic for docs/EXPERIMENTS.md: which template pairs the playbook-fingerprint candidate links
join, which of them are false under ground truth (b), and how large arm D's connected components get.

This is an explanation aid, not a pre-registered measurement: it was run after the E4 results existed, on one
(seed, rotation), and changes nothing.

  python scripts/diagnose_candidates.py --seed 1001 --rotation 0.5
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import eval_metrics as em  # noqa: E402
from generate_dataset import generate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1001)
    ap.add_argument("--rotation", type=float, default=0.5)
    args = ap.parse_args()

    from backend.app.services.replay_service import replay_records
    records = generate(args.seed, args.rotation)
    by = {r["incident_id"]: r for r in records}
    result = replay_records(records)
    truth = em.truth_functions(records)
    cand = em.edges_candidate(result.edges)

    def tid(i: str) -> str:
        return by[i]["campaign_template_id"]

    print(f"seed {args.seed}, rotation {args.rotation}: {len(cand)} candidate links")
    print(f"  true under (a) same instance: {sum(truth['a'](a, b) for a, b in cand)}")
    print(f"  true under (b) same family:   {sum(truth['b'](a, b) for a, b in cand)}")
    wrong = Counter(tuple(sorted((tid(a), tid(b)))) for a, b in cand if not truth["b"](a, b))
    print("  false under (b), by template pair:", dict(wrong.most_common()))
    ids = list(by)
    comp = em.components(ids, em.edges_d(result.edges))
    sizes = Counter(comp.values())
    print("  arm D component sizes (largest first):", sorted(sizes.values(), reverse=True)[:8])
    big = max(sizes, key=sizes.get)
    print("  largest component by template:", dict(Counter(tid(i) for i in ids if comp[i] == big)))
    print("  largest component by script family:", dict(Counter(by[i]["script_family"] for i in ids if comp[i] == big)))
    d3 = [i for i in ids if tid(i) == "D3"]
    print("  D3 decoys linked to a non-D3 incident:",
          sum(1 for a, b in cand if (a in d3) != (b in d3)), "links; D3-D3 links:",
          sum(1 for a, b in cand if a in d3 and b in d3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
