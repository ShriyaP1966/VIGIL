#!/usr/bin/env python3
"""Evaluation harness (blueprint §8). Phase 2 implements two suites:

  tactics    E1: per-label precision/recall/F1 and macro-F1 of the rule extractor on a template split
  injection  E5: share of the 10 attack transcripts that are neutralised (flag fires, labels and risk unchanged)

Every number comes from this script. Results are written to docs/experiments/<suite>_<split>.json together
with the dataset hash, lexicon hash and the exact command, so they can be reproduced.

Honesty notes (also written into each JSON file): all data is synthetic and was written by the same author
as the rules, so scores are optimistic; they do not predict real-world performance. The owner's
hand-written held-out set (suite `heldout`, Phase 5) is the unbiased check. Develop on `dev`; run `test`
once at the end.

Usage:
  python scripts/evaluate_model.py --suite tactics --split dev
  python scripts/evaluate_model.py --suite tactics --split test
  python scripts/evaluate_model.py --suite injection
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("DATABASE_URL", "sqlite://")   # the injection suite uses a throwaway in-memory DB

from ai_engine.extraction.interface import UtteranceInput  # noqa: E402
from ai_engine.extraction.rule_extractor import DEFAULT_LEXICON, RuleExtractor  # noqa: E402
from ai_engine.extraction.tactics import TACTIC_LABELS, stage_sequence_from_labels  # noqa: E402

EXPERIMENTS_DIR = ROOT / "docs" / "experiments"
DEFAULT_DATA = ROOT / "data" / "scenarios.jsonl"
ATTACKS = ROOT / "data" / "injection_attacks.json"
CAVEAT = ("All data is synthetic and written by the same author as the rules, so these scores are optimistic "
          "and do not predict real-world performance. The owner's hand-written held-out set is the unbiased check.")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f1 = 2 * p * r / (p + r) if p is not None and r is not None and (p + r) > 0 else (0.0 if tp + fp + fn else None)
    return {"tp": tp, "fp": fp, "fn": fn, "support": tp + fn, "precision": p, "recall": r, "f1": f1}


def rnd(x):
    return None if x is None else round(x, 4)


def environment() -> dict:
    return {"python": platform.python_version(), "platform": platform.platform()}


def write_result(name: str, payload: dict, no_write: bool) -> None:
    if no_write:
        return
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPERIMENTS_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {path.relative_to(ROOT)}")


# ----------------------------------------------------------------------------------------
# E1: tactics
# ----------------------------------------------------------------------------------------

def suite_tactics(args) -> dict:
    from generate_dataset import load
    everything = load(args.data)
    # Decoys are scored in E3/E4 (do they form a campaign?), not here: their gold tactic labels are mostly empty
    # by design (an awareness notice that quotes a scam is not itself a threat). They are reported separately below.
    records = [r for r in everything
               if (args.split == "all" or r["split"] == args.split) and r["scenario_type"] != "decoy"]
    decoys = [r for r in everything
              if (args.split == "all" or r["split"] == args.split) and r["scenario_type"] == "decoy"]
    extractor = RuleExtractor()

    counts = {lab: Counter() for lab in TACTIC_LABELS}
    by_lang = defaultdict(lambda: Counter())
    errors = {lab: {"false_positives": [], "false_negatives": []} for lab in TACTIC_LABELS}
    seq_exact = seq_total = 0
    inst_ok = pay_ok = inc_total = 0
    n_utt = 0
    stages: list[str] = []

    for r in records:
        inputs = [UtteranceInput(idx=u["idx"], speaker=u["speaker"], text=u["text"]) for u in r["utterances"]]
        res = extractor.analyze(inputs)
        n_utt += len(inputs)
        stages = []
        for u, pred in zip(r["utterances"], res.utterances):
            gold, got = set(u["tactic_labels"]), set(pred.tactic_labels)
            for lab in TACTIC_LABELS:
                key = "tp" if lab in gold and lab in got else "fp" if lab in got else "fn" if lab in gold else None
                if key:
                    counts[lab][key] += 1
                    by_lang[r["language"]][key] += 1
                    if key != "tp" and len(errors[lab]["false_positives" if key == "fp" else "false_negatives"]) < 6:
                        errors[lab]["false_positives" if key == "fp" else "false_negatives"].append(
                            {"incident": r["incident_id"], "language": r["language"], "text": u["text"]})
        # incident level
        stages = stage_sequence_from_labels([p.tactic_labels for p in res.utterances])
        seq_total += 1
        seq_exact += stages == r["expected_stage_sequence"]
        inc_total += 1
        inst_ok += res.institution_class == r["institution_class"]
        pay_ok += res.payment_channel == r["payment_channel"]

    per_label = {lab: {k: rnd(v) if isinstance(v, float) else v for k, v in prf(
        counts[lab]["tp"], counts[lab]["fp"], counts[lab]["fn"]).items()} for lab in TACTIC_LABELS}
    supported = [lab for lab in TACTIC_LABELS if per_label[lab]["support"] > 0]
    macro = sum(per_label[lab]["f1"] for lab in supported) / len(supported) if supported else None
    tp = sum(counts[lab]["tp"] for lab in TACTIC_LABELS)
    fp = sum(counts[lab]["fp"] for lab in TACTIC_LABELS)
    fn = sum(counts[lab]["fn"] for lab in TACTIC_LABELS)
    micro = prf(tp, fp, fn)

    # Decoy side-report: utterances that have NO gold tactic label (awareness notices, benign notices, vague notes)
    # but that the extractor still labels. These are expected weak spots of a keyword/lexicon extractor.
    quiet = flagged = 0
    for r in decoys:
        res = extractor.analyze([UtteranceInput(idx=u["idx"], speaker=u["speaker"], text=u["text"])
                                 for u in r["utterances"]])
        for u, pred in zip(r["utterances"], res.utterances):
            if u["speaker"] != "victim" and not u["tactic_labels"]:
                quiet += 1
                flagged += any(lab != "LEGITIMATE" for lab in pred.tactic_labels)   # a scam label, not LEGITIMATE
    decoy_report = {"utterances_without_gold_labels": quiet, "of_which_labelled_by_extractor": flagged,
                    "rate": rnd(flagged / quiet) if quiet else None}

    meta = records[0] if records else {}
    return {
        "suite": "tactics", "experiment": "E1", "split": args.split,
        "command": f"python scripts/evaluate_model.py --suite tactics --split {args.split}",
        "dataset": {"path": str(args.data.relative_to(ROOT)), "sha256": sha256_of(args.data),
                    "generator_version": meta.get("generator_version"), "seed": meta.get("seed"),
                    "rotation": meta.get("rotation"), "incidents": len(records), "utterances": n_utt,
                    "templates": sorted({r["campaign_template_id"] for r in records})},
        "extractor": {"name": extractor.name, "version": extractor.version,
                      "lexicon_sha256": sha256_of(DEFAULT_LEXICON), "threshold": extractor.threshold},
        "metrics": {
            "macro_f1_over_labels_with_support": rnd(macro),
            "labels_with_support": supported,
            "labels_without_support": [lab for lab in TACTIC_LABELS if lab not in supported],
            "micro": {k: rnd(v) if isinstance(v, float) else v for k, v in micro.items()},
            "per_label": per_label,
            "per_language_micro": {lang: {k: rnd(v) if isinstance(v, float) else v
                                          for k, v in prf(c["tp"], c["fp"], c["fn"]).items()}
                                   for lang, c in sorted(by_lang.items())},
            "incident_stage_sequence_exact_match": rnd(seq_exact / seq_total) if seq_total else None,
            "institution_class_accuracy": rnd(inst_ok / inc_total) if inc_total else None,
            "payment_channel_accuracy": rnd(pay_ok / inc_total) if inc_total else None,
            "decoy_utterances_labelled_despite_no_gold_label": decoy_report,
        },
        "error_examples": errors,
        "caveat": CAVEAT, "environment": environment(),
    }


def print_tactics(result: dict) -> None:
    m = result["metrics"]
    print(f"\nE1 tactics, split={result['split']}  ({result['dataset']['incidents']} incidents, "
          f"{result['dataset']['utterances']} utterances, templates {result['dataset']['templates']})")
    print(f"{'label':26} {'support':>7} {'P':>7} {'R':>7} {'F1':>7}   tp/fp/fn")
    for lab, v in m["per_label"].items():
        f = lambda x: "  n/a " if x is None else f"{x:7.3f}"   # noqa: E731
        print(f"{lab:26} {v['support']:7d} {f(v['precision'])} {f(v['recall'])} {f(v['f1'])}   {v['tp']}/{v['fp']}/{v['fn']}")
    print(f"\nmacro-F1 (labels with support {len(m['labels_with_support'])}): {m['macro_f1_over_labels_with_support']}")
    print(f"micro: P={m['micro']['precision']} R={m['micro']['recall']} F1={m['micro']['f1']}")
    print("per language micro-F1:", {k: v["f1"] for k, v in m["per_language_micro"].items()})
    print(f"stage-sequence exact match: {m['incident_stage_sequence_exact_match']}  "
          f"institution acc: {m['institution_class_accuracy']}  payment acc: {m['payment_channel_accuracy']}")
    d = m["decoy_utterances_labelled_despite_no_gold_label"]
    print(f"decoy utterances with no gold label that the extractor still labels: "
          f"{d['of_which_labelled_by_extractor']}/{d['utterances_without_gold_labels']}")
    if m["labels_without_support"]:
        print("no gold examples in this split for:", ", ".join(m["labels_without_support"]))
    print("\n" + CAVEAT)


# ----------------------------------------------------------------------------------------
# E5: injection robustness
# ----------------------------------------------------------------------------------------

def suite_injection(args) -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from backend.app.core.database import Base
    from backend.app.models import models  # noqa: F401
    from backend.app.models.models import TacticEvent
    from backend.app.schemas.schemas import EvidenceCreate, IncidentCreate
    from backend.app.services.incident_service import create_incident, run_incident_analysis
    from ai_engine.guard.injection import detect_injection

    data = json.loads(ATTACKS.read_text(encoding="utf-8"))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    def analyse(text):
        inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(text=text)]))
        a = run_incident_analysis(db, inc.id)
        labels = sorted({e.label for e in db.query(TacticEvent).filter(TacticEvent.incident_id == inc.id)})
        return a, labels, json.loads(a.injection_flags_json)

    def compose(base, position, injection):
        if position == "start":
            return f"{injection} {base}"
        if position == "end":
            return f"{base} {injection}"
        parts = base.split(". ")
        mid = len(parts) // 2
        return ". ".join(parts[:mid]) + f". {injection} " + ". ".join(parts[mid:])

    rows = []
    for atk in data["attacks"]:
        base = data["bases"][atk["base"]]
        clean, clean_labels, _ = analyse(base)
        attacked, atk_labels, flags = analyse(compose(base, atk["position"], atk["injection"]))
        flagged = bool(flags) and bool(detect_injection(atk["injection"]))
        unchanged = atk_labels == clean_labels and attacked.risk_score == clean.risk_score
        rows.append({"id": atk["id"], "flagged": flagged, "labels_unchanged": atk_labels == clean_labels,
                     "risk_clean": clean.risk_score, "risk_attacked": attacked.risk_score,
                     "neutralised": flagged and unchanged, "flags": flags})
    neutralised = sum(r["neutralised"] for r in rows)
    return {
        "suite": "injection", "experiment": "E5", "split": "all",
        "command": "python scripts/evaluate_model.py --suite injection",
        "dataset": {"path": str(ATTACKS.relative_to(ROOT)), "sha256": sha256_of(ATTACKS), "attacks": len(rows)},
        "metrics": {"neutralised": neutralised, "total": len(rows),
                    "neutralised_rate": rnd(neutralised / len(rows)),
                    "flagged_rate": rnd(sum(r["flagged"] for r in rows) / len(rows))},
        "per_attack": rows,
        "caveat": ("The attacks and the guard were written by the same author, and the rule-based extractor is "
                   "largely inert to such text, so this only shows the guard recognises these phrasings and "
                   "locks mitigation. It says nothing about novel or obfuscated attacks (see the guard's "
                   "documented limitations)."),
        "environment": environment(),
    }


def print_injection(result: dict) -> None:
    m = result["metrics"]
    print(f"\nE5 injection: {m['neutralised']}/{m['total']} neutralised "
          f"(flagged {m['flagged_rate']}, rate {m['neutralised_rate']})")
    for r in result["per_attack"]:
        print(f"  {r['id']}: flagged={r['flagged']} labels_unchanged={r['labels_unchanged']} "
              f"risk {r['risk_clean']} -> {r['risk_attacked']}  {r['flags']}")
    print("\n" + result["caveat"])


# ----------------------------------------------------------------------------------------
# Association experiments: arm A, per-run scoring, E3 integrity, E4 rotation (docs/PREREGISTRATION.md)
# ----------------------------------------------------------------------------------------

import eval_metrics as em  # noqa: E402

TAU_GRID = [round(0.10 + 0.05 * i, 2) for i in range(17)]      # 0.10 ... 0.90
CAL_SEED, CAL_ROTATION = 900, 0.5                               # dev-only calibration (never an evaluation seed)
EVAL_SEED_BASE = 1000                                           # evaluation seeds are 1001 ... 1000 + n
ROTATION_LEVELS = [0.0, 0.25, 0.5, 0.75, 1.0]
ARMS = ["A", "B", "C", "D"]
GROUND_TRUTHS = ["a", "b"]
SLICES = ["all", "test"]
HASHED = ["scripts/generate_dataset.py", "data/lexicon.json", "ai_engine/fingerprint/similarity.py",
          "config/counter_evidence_rules.json", "data/public_identifiers.json"]


def sha256_lf(path: Path) -> str:
    """sha256 with CRLF normalised to LF, so the value does not depend on the checkout's line endings."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def incident_text(rec: dict) -> str:
    return " ".join(u["text"] for u in rec["utterances"])


def scam_gate(records: list[dict]) -> set[str]:
    """Arm A's "incident-level classification": ids with at least one non-LEGITIMATE tactic label."""
    extractor = RuleExtractor()
    gated = set()
    for r in records:
        res = extractor.analyze([UtteranceInput(idx=u["idx"], speaker=u["speaker"], text=u["text"])
                                 for u in r["utterances"]])
        if any(lab != "LEGITIMATE" for p in res.utterances for lab in p.tactic_labels):
            gated.add(r["incident_id"])
    return gated


def arm_a_similarities(records: list[dict], gated: set[str]):
    """Cosine similarity matrix of TF-IDF vectors over the gated incidents (fitted on those incidents)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    ids = sorted(gated)
    by_id = {r["incident_id"]: r for r in records}
    if len(ids) < 2:
        return ids, None
    X = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True).fit_transform(
        [incident_text(by_id[i]) for i in ids])
    return ids, (X @ X.T).toarray()


def arm_a_edges(ids: list[str], sim, tau: float) -> list[tuple[str, str]]:
    if sim is None:
        return []
    return [(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids)) if sim[i][j] >= tau]


def calibrate_tau_a() -> dict:
    """tau_A on DEV only: seed 900, r = 0.5, the `dev` split, maximise pairwise F1 under ground truth (a); ties go
    to the larger tau_A (docs/PREREGISTRATION.md section 4)."""
    from generate_dataset import generate
    records = generate(CAL_SEED, CAL_ROTATION)
    dev = [r for r in records if r["split"] == "dev"]
    ids_dev = [r["incident_id"] for r in dev]
    truth, benign = em.truth_functions(dev)["a"], em.benign_ids(dev)
    gated = scam_gate(dev)
    ids, sim = arm_a_similarities(dev, gated)
    table = []
    for tau in TAU_GRID:
        comp = em.components(ids_dev, arm_a_edges(ids, sim, tau))
        m = em.pairwise(ids_dev, comp, truth, benign)
        table.append({"tau": tau, "precision": rnd(m["precision"]), "recall": rnd(m["recall"]), "f1": rnd(m["f1"])})
    best = max(table, key=lambda row: ((row["f1"] or 0.0), row["tau"]))
    return {"seed": CAL_SEED, "rotation": CAL_ROTATION, "split": "dev", "ground_truth": "a",
            "incidents": len(dev), "chosen_tau_a": best["tau"], "table": table}


def arm_edge_sets(records: list[dict], edges, tau_a: float) -> dict[str, list[tuple[str, str]]]:
    gated = scam_gate(records)
    ids, sim = arm_a_similarities(records, gated)
    return {"A": arm_a_edges(ids, sim, tau_a), "B": em.edges_b(edges), "C": em.edges_c(edges),
            "D": em.edges_d(edges)}


def score_run(records: list[dict], edges, tau_a: float) -> dict:
    """All pairwise metrics of one run: slice -> ground truth -> arm (and candidate scores for D)."""
    all_ids = [r["incident_id"] for r in records]
    sets = arm_edge_sets(records, edges, tau_a)
    comps = {arm: em.components(all_ids, e) for arm, e in sets.items()}
    truths, benign = em.truth_functions(records), em.benign_ids(records)
    slices = {"all": all_ids, "test": [r["incident_id"] for r in records if r["split"] == "test"]}
    out: dict = {}
    for sl, scored in slices.items():
        out[sl] = {}
        for g in GROUND_TRUTHS:
            out[sl][g] = {arm: {k: rnd(v) if isinstance(v, float) else v
                                for k, v in em.pairwise(scored, comps[arm], truths[g], benign).items()}
                          for arm in ARMS}
            cs = em.candidate_scores(scored, em.edges_candidate(edges), comps["C"], comps["D"], truths[g])
            out[sl][g]["D"].update({k: rnd(v) if isinstance(v, float) else v for k, v in cs.items()})
    return out


def association_integrity(records: list[dict], result) -> dict:
    """E3 counters for one run (docs/PREREGISTRATION.md section 6)."""
    from ai_engine.extraction.entity_extractor import extract_entities
    from ai_engine.extraction.normalisation import normalise_text
    by_id = {r["incident_id"]: r for r in records}
    benign = em.benign_ids(records)
    found: dict[str, set[str]] = {}

    def identifiers(iid: str) -> set[str]:
        if iid not in found:
            found[iid] = {f"{e.entity_type}:{e.canonical_value}"
                          for e in extract_entities(normalise_text(incident_text(by_id[iid])))}
        return found[iid]

    i1 = [e for e in result.edges if e.status == "OBSERVED_MATCH" and (
        not e.shared or e.match_type not in em.EXACT_TYPES
        or not all(s in identifiers(e.a) and s in identifiers(e.b) for s in e.shared))]

    def touching(pairs):
        return [(a, b) for a, b in pairs if a in benign or b in benign]

    b_edges, c_edges, cand = em.edges_b(result.edges), em.edges_c(result.edges), em.edges_candidate(result.edges)
    linked_c = {i for e in c_edges for i in e}
    linked_d = linked_c | {i for e in cand for i in e}
    negatives = [r["incident_id"] for r in records if r["scenario_type"] == "legitimate"]
    decoys: dict[str, dict] = {}
    for r in records:
        if r["scenario_type"] == "decoy":
            d = decoys.setdefault(r["decoy_type"], {"total": 0, "linked_observed": 0, "linked_observed_or_candidate": 0})
            d["total"] += 1
            d["linked_observed"] += r["incident_id"] in linked_c
            d["linked_observed_or_candidate"] += r["incident_id"] in linked_d
    benign_campaigns = [c for c in result.campaigns if any(m in benign for m in c["members"])]
    return {
        "i1_violations": len(i1),
        "i1_violation_examples": [{"a": e.a, "b": e.b, "shared": list(e.shared), "match_type": e.match_type}
                                  for e in i1[:5]],
        "observed_edges_total": len(c_edges),
        "identifier_edges_touching_benign_before_counter_evidence": len(touching(b_edges)),
        "observed_edges_touching_benign_after_counter_evidence": len(touching(c_edges)),
        "candidate_edges_total": len(cand),
        "candidate_edges_touching_benign": len(touching(cand)),
        "negatives_total": len(negatives),
        "negatives_with_observed_edge": sum(n in linked_c for n in negatives),
        "negatives_with_observed_or_candidate_edge": sum(n in linked_d for n in negatives),
        "decoys": decoys,
        "campaign_hypotheses": len(result.campaigns),
        "campaign_hypotheses_containing_a_negative_or_decoy": len(benign_campaigns),
    }


def _run_one(job: tuple[int, float, float]) -> dict:
    """One (seed, r) run: generate, replay through the real pipeline, score. Top-level so it can be pickled."""
    seed, rotation, tau_a = job
    from generate_dataset import generate
    from backend.app.services.replay_service import replay_records
    records = generate(seed, rotation)
    result = replay_records(records)
    by_status = Counter(f"{e.status}/{e.match_type}" for e in result.edges)
    return {"seed": seed, "rotation": rotation, "incidents": len(records), "edge_counts": dict(sorted(by_status.items())),
            "scores": score_run(records, result.edges, tau_a), "integrity": association_integrity(records, result)}


def aggregate_runs(runs: list[dict]) -> dict:
    """slice -> ground truth -> rotation level -> arm -> metric -> {mean, std, n} over seeds."""
    metrics = ["precision", "recall", "f1", "far", "far_benign"]
    cand_metrics = ["candidate_precision", "candidate_recall"]
    out: dict = {}
    for sl in SLICES:
        out[sl] = {}
        for g in GROUND_TRUTHS:
            out[sl][g] = {}
            for level in sorted({r["rotation"] for r in runs}):
                at = [r for r in runs if r["rotation"] == level]
                out[sl][g][str(level)] = {
                    arm: {m: em.mean_std([r["scores"][sl][g][arm][m] for r in at])
                          for m in metrics + (cand_metrics if arm == "D" else [])}
                    for arm in ARMS}
    return out


def pooled_integrity(runs: list[dict]) -> dict:
    """E3 counters summed over every run (all seeds and rotation levels)."""
    keys = ["i1_violations", "observed_edges_total", "identifier_edges_touching_benign_before_counter_evidence",
            "observed_edges_touching_benign_after_counter_evidence", "candidate_edges_total",
            "candidate_edges_touching_benign", "negatives_total", "negatives_with_observed_edge",
            "negatives_with_observed_or_candidate_edge", "campaign_hypotheses",
            "campaign_hypotheses_containing_a_negative_or_decoy"]
    pooled = {k: sum(r["integrity"][k] for r in runs) for k in keys}
    decoys: dict[str, Counter] = {}
    for r in runs:
        for name, d in r["integrity"]["decoys"].items():
            decoys.setdefault(name, Counter()).update(d)
    pooled["decoys"] = {k: dict(v) for k, v in sorted(decoys.items())}
    pooled["runs"] = len(runs)
    return pooled


def suite_rotation(args) -> dict:
    from concurrent.futures import ProcessPoolExecutor
    calibration = calibrate_tau_a()
    tau_a = calibration["chosen_tau_a"]
    seeds = [EVAL_SEED_BASE + i for i in range(1, args.seeds + 1)]
    jobs = [(seed, level, tau_a) for level in ROTATION_LEVELS for seed in seeds]
    print(f"tau_A (dev only) = {tau_a}; {len(jobs)} runs on {args.workers} workers", flush=True)
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            runs = list(pool.map(_run_one, jobs))
    else:
        runs = [_run_one(j) for j in jobs]
    from backend.app.services.incident_service import settings as svc_settings
    return {
        "suite": "rotation", "experiment": "E4",
        "command": f"python scripts/evaluate_model.py --suite rotation --seeds {args.seeds}",
        "preregistration": "docs/PREREGISTRATION.md",
        "design": {"rotation_levels": ROTATION_LEVELS, "seeds": seeds, "t_candidate": svc_settings.T_CANDIDATE,
                   "arms": {"A": "TF-IDF text similarity over incidents with a scam tactic label",
                            "B": "components over exact-identifier links (counter-evidence not applied)",
                            "C": "B after the counter-evidence engine (CE-1,2,3,4,5,7; CE-6 and CE-8 not implemented)",
                            "D": "C plus playbook-fingerprint candidate links"},
                   "ground_truths": {"a": "true pair = same campaign_instance_id",
                                     "b": "true pair = same script family (digital_arrest = T1+T2+T3, bank_kyc = T4, "
                                          "payment_link = T5, courier_customs = T6)"},
                   "std": "sample standard deviation (n - 1) over seeds",
                   "slices": {"all": "all 150 incidents", "test": "the test-split incidents only (T3, T6, N5, N6, D3, D4)"}},
        "calibration_tau_a": calibration,
        "artefact_sha256_lf": {p: sha256_lf(ROOT / p) for p in HASHED},
        "aggregate": aggregate_runs(runs),
        "integrity_pooled": pooled_integrity(runs),
        "runs": runs,
        "caveat": ("All data is synthetic and the generator, lexicon and rules share an author, so these numbers "
                   "describe behaviour on this generator and do not imply real-world performance."),
        "environment": environment(),
    }


def print_rotation(result: dict) -> None:
    print(f"\nE4 rotation, tau_A={result['calibration_tau_a']['chosen_tau_a']}, "
          f"seeds {result['design']['seeds'][0]}-{result['design']['seeds'][-1]}")
    for sl in SLICES:
        for g in GROUND_TRUTHS:
            print(f"\n[{sl} incidents, ground truth ({g})]  pairwise F1 / FAR  (mean over seeds)")
            print(f"{'r':>5} " + " ".join(f"{a + ' F1':>9} {a + ' FAR':>9}" for a in ARMS))
            for level, arms in result["aggregate"][sl][g].items():
                cells = []
                for a in ARMS:
                    f, far = arms[a]["f1"]["mean"], arms[a]["far"]["mean"]
                    cells.append(f"{'n/a' if f is None else f'{f:.3f}':>9} {'n/a' if far is None else f'{far:.4f}':>9}")
                print(f"{level:>5} " + " ".join(cells))
    p = result["integrity_pooled"]
    print(f"\nE3 pooled over {p['runs']} runs: I1 violations {p['i1_violations']}, observed links touching a "
          f"negative/decoy after counter-evidence {p['observed_edges_touching_benign_after_counter_evidence']} "
          f"(before: {p['identifier_edges_touching_benign_before_counter_evidence']})")


def suite_associations(args) -> dict:
    """E3 on the committed sample (data/scenarios.jsonl), plus the arm edge counts."""
    from generate_dataset import load
    from backend.app.services.replay_service import replay_records
    records = load(args.data)
    result = replay_records(records)
    meta = records[0]
    return {
        "suite": "associations", "experiment": "E3", "split": "all",
        "command": "python scripts/evaluate_model.py --suite associations",
        "dataset": {"path": str(args.data.relative_to(ROOT)), "sha256_lf": sha256_lf(args.data),
                    "generator_version": meta["generator_version"], "seed": meta["seed"],
                    "rotation": meta["rotation"], "incidents": len(records)},
        "t_candidate": 0.75,
        "edge_counts": dict(sorted(Counter(f"{e.status}/{e.match_type}" for e in result.edges).items())),
        "integrity": association_integrity(records, result),
        "caveat": ("An OBSERVED_MATCH between two benign notices that cite the same official helpline satisfies "
                   "invariant I1 (the identifiers ARE equal), so it is reported separately from I1 violations; "
                   "counter-evidence rule CE-3 is what is expected to withdraw it."),
        "environment": environment(),
    }


def print_associations(result: dict) -> None:
    i = result["integrity"]
    print(f"\nE3 on {result['dataset']['incidents']} incidents: edges {result['edge_counts']}")
    for k, v in i.items():
        if k not in ("decoys", "i1_violation_examples"):
            print(f"  {k}: {v}")
    print("  decoys:", i["decoys"])


# ----------------------------------------------------------------------------------------
# E6: the owner's hand-written held-out set (run once, last)
# ----------------------------------------------------------------------------------------

HELDOUT_FILE = ROOT / "data" / "heldout" / "heldout.jsonl"
HELDOUT_RESULT = EXPERIMENTS_DIR / "heldout.json"


class HeldoutRefused(RuntimeError):
    pass


def load_heldout(path: Path) -> list[dict]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise HeldoutRefused(f"{path.name} line {n} is not valid JSON: {e}") from None
        for key in ("id", "source_channel", "language", "is_legitimate", "utterances"):
            if key not in row:
                raise HeldoutRefused(f"{path.name} line {n}: missing field {key!r}")
        for u in row["utterances"]:
            bad = [lab for lab in u.get("tactic_labels", []) if lab not in TACTIC_LABELS]
            if bad:
                raise HeldoutRefused(f"{path.name} {row['id']}: unknown tactic labels {bad}")
        rows.append(row)
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise HeldoutRefused("duplicate ids in the held-out file")
    return rows


def suite_heldout(args, path: Path = HELDOUT_FILE, result_path: Path = HELDOUT_RESULT) -> dict:
    """Refuses to run on an empty file or a second time. The file is read only here, when asked for."""
    if result_path.exists():
        raise HeldoutRefused(f"{result_path.name} already exists: the held-out set is evaluated once, so it will "
                             "not be run again. The first result stands.")
    rows = load_heldout(path)
    if not rows:
        raise HeldoutRefused(f"{path.name} is empty: the owner has not marked the held-out set as ready.")
    extractor = RuleExtractor()
    counts = {lab: Counter() for lab in TACTIC_LABELS}
    legit_total = legit_fp = 0
    for row in rows:
        res = extractor.analyze([UtteranceInput(idx=i, speaker=u.get("speaker", "unknown"), text=u["text"])
                                 for i, u in enumerate(row["utterances"])])
        any_scam = False
        for u, pred in zip(row["utterances"], res.utterances):
            gold, got = set(u.get("tactic_labels", [])), set(pred.tactic_labels)
            any_scam |= any(lab != "LEGITIMATE" for lab in got)
            for lab in TACTIC_LABELS:
                key = "tp" if lab in gold and lab in got else "fp" if lab in got else "fn" if lab in gold else None
                if key:
                    counts[lab][key] += 1
        if row["is_legitimate"]:
            legit_total += 1
            legit_fp += any_scam
    per_label = {lab: {k: rnd(v) if isinstance(v, float) else v
                       for k, v in prf(c["tp"], c["fp"], c["fn"]).items()} for lab, c in counts.items()}
    supported = [lab for lab in TACTIC_LABELS if per_label[lab]["support"] > 0]
    macro = sum(per_label[lab]["f1"] for lab in supported) / len(supported) if supported else None
    return {
        "suite": "heldout", "experiment": "E6", "command": "python scripts/evaluate_model.py --suite heldout",
        "dataset": {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name,
                    "sha256_lf": sha256_lf(path), "scenarios": len(rows)},
        "extractor": {"name": extractor.name, "version": extractor.version,
                      "lexicon_sha256": sha256_of(DEFAULT_LEXICON)},
        "metrics": {"macro_f1_over_labels_with_support": rnd(macro), "labels_with_support": supported,
                    "per_label": per_label,
                    "legitimate_scenarios": legit_total, "legitimate_false_positives": legit_fp,
                    "legitimate_false_positive_rate": rnd(legit_fp / legit_total) if legit_total else None},
        "caveat": "Written by the project owner, evaluated once. Small and synthetic: indicative, not statistical proof.",
        "environment": environment(),
    }


# ----------------------------------------------------------------------------------------
# E2: entities, E7: latency
# ----------------------------------------------------------------------------------------

ENTITY_TYPES = ("PHONE", "UPI_HANDLE", "DOMAIN")      # the types the generator annotates


def suite_entities(args) -> dict:
    from ai_engine.extraction.entity_extractor import extract_entities
    from ai_engine.extraction.normalisation import normalise_text
    from generate_dataset import load
    records = [r for r in load(args.data) if args.split == "all" or r["split"] == args.split]
    c = {t: Counter() for t in ENTITY_TYPES}
    for r in records:
        gold = {(m["type"], m["canonical"]) for m in r["entity_mentions"]}
        got = {(e.entity_type, e.canonical_value) for e in extract_entities(normalise_text(incident_text(r)))
               if e.entity_type in ENTITY_TYPES}
        for t in ENTITY_TYPES:
            g, p = {x for x in gold if x[0] == t}, {x for x in got if x[0] == t}
            c[t]["tp"] += len(g & p)
            c[t]["fp"] += len(p - g)
            c[t]["fn"] += len(g - p)
    return {"suite": "entities", "experiment": "E2", "split": args.split,
            "command": f"python scripts/evaluate_model.py --suite entities --split {args.split}",
            "dataset": {"path": str(args.data.relative_to(ROOT)), "sha256_lf": sha256_lf(args.data),
                        "incidents": len(records)},
            "metrics": {t: {k: rnd(v) if isinstance(v, float) else v
                            for k, v in prf(c[t]["tp"], c[t]["fp"], c[t]["fn"]).items()} for t in ENTITY_TYPES},
            "scope": "PHONE, UPI_HANDLE and DOMAIN only: bank account numbers carry no gold annotation. "
                     "Spoken-out numbers (decoy D4) are gold-empty and are not extractable by design.",
            "caveat": CAVEAT, "environment": environment()}


def suite_latency(args) -> dict:
    """E7: wall-clock per stage on this machine for the committed sample. Machine-dependent, so it is descriptive."""
    import statistics
    import time
    from generate_dataset import load
    from ai_engine.extraction.entity_extractor import extract_entities
    from ai_engine.extraction.normalisation import normalise_text
    from ai_engine.privacy.redaction import redact_text
    from backend.app.core.database import Base
    from backend.app.services import replay_service as rs
    from backend.app.services.incident_service import create_incident, run_incident_analysis
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    records = load(args.data)
    extractor = RuleExtractor()

    def timed(fn, items):
        out = []
        for it in items:
            t = time.perf_counter()
            fn(it)
            out.append((time.perf_counter() - t) * 1000)
        return out

    stages = {
        "redaction": timed(lambda r: redact_text(incident_text(r)), records),
        "entity_extraction": timed(lambda r: extract_entities(normalise_text(incident_text(r))), records),
        "tactic_extraction": timed(lambda r: extractor.analyze(
            [UtteranceInput(idx=u["idx"], speaker=u["speaker"], text=u["text"]) for u in r["utterances"]]), records),
    }
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    ordered = sorted(records, key=lambda r: (r["timestamp"], r["incident_id"]))
    end_to_end = []
    for r in ordered:
        t = time.perf_counter()
        inc = create_incident(db, rs._incident_payload(r))
        run_incident_analysis(db, inc.id)
        end_to_end.append((time.perf_counter() - t) * 1000)
    db.close()
    engine.dispose()

    def summary(xs):
        xs = sorted(xs)
        return {"n": len(xs), "mean_ms": round(statistics.fmean(xs), 2), "median_ms": round(statistics.median(xs), 2),
                "p95_ms": round(xs[int(0.95 * (len(xs) - 1))], 2), "max_ms": round(xs[-1], 2)}

    return {"suite": "latency", "experiment": "E7", "command": "python scripts/evaluate_model.py --suite latency",
            "dataset": {"path": str(args.data.relative_to(ROOT)), "incidents": len(records)},
            "stages_ms": {k: summary(v) for k, v in stages.items()},
            "end_to_end_ms": {**summary(end_to_end),
                              "first_20_mean_ms": round(statistics.fmean(end_to_end[:20]), 2),
                              "last_20_mean_ms": round(statistics.fmean(end_to_end[-20:]), 2)},
            "note": ("End to end = create_incident + run_incident_analysis through the real services into one growing "
                     "in-memory database, so it includes comparing the new incident with every earlier one; the "
                     "last-20 mean shows that growth. Machine-dependent and descriptive, no threshold."),
            "environment": environment()}


def main() -> int:
    ap = argparse.ArgumentParser(description="VIGIL evaluation harness")
    ap.add_argument("--suite", required=True,
                    choices=["tactics", "entities", "associations", "rotation", "injection", "heldout", "latency"])
    ap.add_argument("--split", default="dev", choices=["train", "dev", "test", "all"])
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--seeds", type=int, default=10, help="rotation suite: number of seeds (1001 ...)")
    ap.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 2)))
    ap.add_argument("--no-write", action="store_true", help="print only; do not write docs/experiments")
    args = ap.parse_args()

    if args.suite == "tactics":
        result = suite_tactics(args)
        print_tactics(result)
        write_result(f"tactics_{args.split}", result, args.no_write)
    elif args.suite == "injection":
        result = suite_injection(args)
        print_injection(result)
        write_result("injection", result, args.no_write)
    elif args.suite == "associations":
        result = suite_associations(args)
        print_associations(result)
        write_result("associations", result, args.no_write)
    elif args.suite == "rotation":
        result = suite_rotation(args)
        print_rotation(result)
        write_result("rotation", result, args.no_write)
    elif args.suite == "entities":
        result = suite_entities(args)
        print(json.dumps(result["metrics"], indent=1))
        write_result(f"entities_{args.split}", result, args.no_write)
    elif args.suite == "latency":
        result = suite_latency(args)
        print(json.dumps({"stages_ms": result["stages_ms"], "end_to_end_ms": result["end_to_end_ms"]}, indent=1))
        write_result("latency", result, args.no_write)
    else:
        try:
            result = suite_heldout(args)
        except HeldoutRefused as e:
            print(f"REFUSED: {e}")
            return 2
        print(json.dumps(result["metrics"], indent=1))
        write_result("heldout", result, args.no_write)
    return 0


if __name__ == "__main__":
    sys.exit(main())
