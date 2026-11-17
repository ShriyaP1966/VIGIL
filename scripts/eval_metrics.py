"""Pure metric functions for the association experiments (E3, E4). No I/O, no database, no randomness.

Definitions follow docs/PREREGISTRATION.md (written before any experiment ran).

F1 convention (stated before any experiment): F1 is 0.0 when there is at least one predicted or true pair but no
true positive, and `None` only when there is no predicted and no true pair at all. Precision is `None` when
nothing was predicted, recall is `None` when there is no true pair; `None` is never replaced by 0 or 1.
"""

from __future__ import annotations

import statistics
from itertools import combinations
from typing import Callable, Iterable

# --- arm edge selectors (ReplayResult.edges, see backend/app/services/replay_service.py) -------------------------

EXACT_TYPES = ("EXACT_IDENTIFIER", "COMBINED")


def edges_b(edges) -> list[tuple[str, str]]:
    """B: exact identifier equality, counter-evidence NOT applied (a disputed link is still an identifier link)."""
    return [(e.a, e.b) for e in edges
            if e.match_type in EXACT_TYPES and e.status in ("OBSERVED_MATCH", "DISPUTED_ASSOCIATION")]


def edges_c(edges) -> list[tuple[str, str]]:
    """C: observed matches that survived the counter-evidence engine."""
    return [(e.a, e.b) for e in edges if e.status == "OBSERVED_MATCH"]


def edges_d(edges) -> list[tuple[str, str]]:
    """D: observed matches plus fingerprint candidates (neither disputed nor rejected)."""
    return [(e.a, e.b) for e in edges if e.status in ("OBSERVED_MATCH", "CANDIDATE_ASSOCIATION")]


def edges_candidate(edges) -> list[tuple[str, str]]:
    return [(e.a, e.b) for e in edges if e.status == "CANDIDATE_ASSOCIATION"]


# --- components ---------------------------------------------------------------------------------------------------

def components(ids: Iterable[str], edges: Iterable[tuple[str, str]]) -> dict[str, int]:
    """Connected components (union-find). Returns id -> component label; unlinked ids are singletons."""
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        if a in parent and b in parent:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    return {i: find(i) for i in parent}


# --- ground truth -------------------------------------------------------------------------------------------------

def truth_functions(records: list[dict]) -> dict[str, Callable[[str, str], bool]]:
    inst = {r["incident_id"]: r["campaign_instance_id"] for r in records}
    fam = {r["incident_id"]: r["script_family"] for r in records}
    return {
        "a": lambda i, j: inst[i] is not None and inst[i] == inst[j],
        "b": lambda i, j: fam[i] is not None and fam[i] == fam[j],
    }


def benign_ids(records: list[dict]) -> set[str]:
    return {r["incident_id"] for r in records if r["scenario_type"] in ("legitimate", "decoy")}


# --- metrics ------------------------------------------------------------------------------------------------------

def _prf(tp: int, fp: int, fn: int) -> tuple[float | None, float | None, float | None]:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    if p is not None and r is not None and p + r > 0:
        f1 = 2 * p * r / (p + r)
    else:
        f1 = 0.0 if tp + fp + fn else None
    return p, r, f1


def pairwise(scored: list[str], comp: dict[str, int], true_pair: Callable[[str, str], bool], benign: set[str]) -> dict:
    """Pairwise precision/recall/F1 and false association rates over all unordered pairs of `scored` incidents."""
    tp = fp = fn = tn = 0
    fp_benign = tn_benign = 0
    for i, j in combinations(sorted(scored), 2):
        predicted, true = comp[i] == comp[j], true_pair(i, j)
        if predicted and true:
            tp += 1
        elif predicted:
            fp += 1
        elif true:
            fn += 1
        else:
            tn += 1
        if not true and (i in benign or j in benign):
            fp_benign += predicted
            tn_benign += not predicted
    p, r, f1 = _prf(tp, fp, fn)
    far = fp / (fp + tn) if fp + tn else None
    far_benign = fp_benign / (fp_benign + tn_benign) if fp_benign + tn_benign else None
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": p, "recall": r, "f1": f1,
            "far": far, "far_benign": far_benign}


def candidate_scores(scored: list[str], cand_edges: list[tuple[str, str]], comp_c: dict[str, int],
                     comp_d: dict[str, int], true_pair: Callable[[str, str], bool]) -> dict:
    """Candidate precision: share of candidate edges that are true pairs. Candidate recall: of the true pairs that
    arm C does not connect, the share that arm D connects."""
    inside = set(scored)
    edges = [(a, b) for a, b in cand_edges if a in inside and b in inside]
    true_edges = sum(true_pair(a, b) for a, b in edges)
    uncovered = recovered = 0
    for i, j in combinations(sorted(scored), 2):
        if true_pair(i, j) and comp_c[i] != comp_c[j]:
            uncovered += 1
            recovered += comp_d[i] == comp_d[j]
    return {"candidate_edges": len(edges), "candidate_true": true_edges,
            "candidate_precision": true_edges / len(edges) if edges else None,
            "uncovered_true_pairs": uncovered, "recovered_by_candidates": recovered,
            "candidate_recall": recovered / uncovered if uncovered else None}


def mean_std(values: list[float | None]) -> dict:
    """Mean and SAMPLE standard deviation (n - 1) over the defined values; `n` says how many seeds defined it."""
    xs = [v for v in values if v is not None]
    if not xs:
        return {"mean": None, "std": None, "n": 0}
    return {"mean": round(statistics.fmean(xs), 4),
            "std": round(statistics.stdev(xs), 4) if len(xs) > 1 else None, "n": len(xs)}
