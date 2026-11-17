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


def main() -> int:
    ap = argparse.ArgumentParser(description="VIGIL evaluation harness")
    ap.add_argument("--suite", required=True, choices=["tactics", "injection"])
    ap.add_argument("--split", default="dev", choices=["train", "dev", "test", "all"])
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--no-write", action="store_true", help="print only; do not write docs/experiments")
    args = ap.parse_args()

    if args.suite == "tactics":
        result = suite_tactics(args)
        print_tactics(result)
        write_result(f"tactics_{args.split}", result, args.no_write)
    else:
        result = suite_injection(args)
        print_injection(result)
        write_result("injection", result, args.no_write)
    return 0


if __name__ == "__main__":
    sys.exit(main())
