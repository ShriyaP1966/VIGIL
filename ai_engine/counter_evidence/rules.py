"""Counter-evidence rules (blueprint §6.10): why two incidents might NOT be related.

Each rule inspects one pair of incidents (one association) and returns zero or more Findings. A finding
always states the contradictory observation, the evidence it came from, its severity, its effect on the
association's confidence and a plain-language explanation. Findings are stored separately and shown next
to the association; they are never folded into an opaque score. Pure functions: no database access.

Implemented: CE-1, CE-2, CE-3, CE-5, CE-7, and CE-4 minimally. Deferred: CE-6, CE-8 (config/counter_evidence_rules.json).
Language and channel differences are context, not contradiction: CE-7 is LOW (-0.02) and never disputes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ai_engine.counter_evidence.public_identifiers import PublicIdentifiers, get_public_identifiers
from ai_engine.fingerprint.similarity import Fingerprint, order_consistency

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "counter_evidence_rules.json"


@dataclass(frozen=True)
class SharedIdentifier:
    type: str
    canonical: str
    display: str
    evidence_refs: tuple[dict, ...] = ()
    min_extraction_confidence: float = 1.0


@dataclass(frozen=True)
class PaymentHandle:
    canonical: str
    display: str
    evidence_id: int
    incident_id: int


@dataclass(frozen=True)
class PairContext:
    incident_a: int
    incident_b: int
    fp_a: Fingerprint
    fp_b: Fingerprint
    shared: tuple[SharedIdentifier, ...] = ()
    handles_a: tuple[PaymentHandle, ...] = ()
    handles_b: tuple[PaymentHandle, ...] = ()
    legitimate: dict[int, bool] = field(default_factory=dict)      # incident id -> labelled legitimate
    stage_refs_a: tuple[dict, ...] = ()                            # one excerpt per detected stage
    stage_refs_b: tuple[dict, ...] = ()


@dataclass(frozen=True)
class Finding:
    rule_id: str
    kind: str
    severity: str                 # LOW | MEDIUM | HIGH
    confidence_impact: float      # negative
    observation: str
    explanation: str
    evidence_refs: list[dict]
    rule_version: str


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rule_cfg(config: dict, rule_id: str) -> dict:
    return next(r for r in config["rules"] if r["id"] == rule_id)


def _finding(config: dict, rule_id: str, observation: str, explanation: str, refs: list[dict]) -> Finding:
    cfg = _rule_cfg(config, rule_id)
    return Finding(rule_id, cfg["kind"], cfg["severity"], float(cfg["confidence_impact"]),
                   observation, explanation, refs, config["version"])


def _stage_refs(ctx: PairContext, stages: set[str] | None = None) -> list[dict]:
    refs = [r for r in (*ctx.stage_refs_a, *ctx.stage_refs_b) if stages is None or r.get("stage") in stages]
    return [{k: r[k] for k in ("evidence_id", "incident_id", "stage", "excerpt", "span") if k in r} for r in refs]


# ---------------------------------------------------------------------------------------------
# CE-1  incompatible chronology (HIGH)
# ---------------------------------------------------------------------------------------------

def ce1_incompatible_chronology(ctx: PairContext, config: dict) -> list[Finding]:
    p = _rule_cfg(config, "CE-1")["params"]
    shared = [s for s in ctx.fp_a.sequence if s in ctx.fp_b.sequence]
    if len(shared) < p["min_shared_stages"]:
        return []
    order_ok = order_consistency(ctx.fp_a.sequence, ctx.fp_b.sequence)
    if order_ok >= p["max_order_consistency"]:
        return []
    return [_finding(
        config, "CE-1",
        f"{len(shared)} shared stages ({', '.join(shared)}) occur in conflicting order; only "
        f"{order_ok:.0%} of the stage pairs appear in the same relative order.",
        "A script usually runs in one order. The same tactics in a conflicting order are weak evidence that "
        "the two incidents come from the same playbook.",
        _stage_refs(ctx, set(shared)),
    )]


# ---------------------------------------------------------------------------------------------
# CE-2  different payment destination (MEDIUM)
# ---------------------------------------------------------------------------------------------

def ce2_different_payment_destination(ctx: PairContext, config: dict) -> list[Finding]:
    p = _rule_cfg(config, "CE-2")["params"]
    anchors = [s for s in ctx.shared if s.type in p["anchor_types"]]
    if not anchors or not ctx.handles_a or not ctx.handles_b:
        return []
    a, b = {h.canonical for h in ctx.handles_a}, {h.canonical for h in ctx.handles_b}
    if a & b:
        return []
    shown_a = ", ".join(sorted({h.display for h in ctx.handles_a}))
    shown_b = ", ".join(sorted({h.display for h in ctx.handles_b}))
    refs = [{"evidence_id": h.evidence_id, "incident_id": h.incident_id, "entity": h.display}
            for h in (*ctx.handles_a, *ctx.handles_b)]
    return [_finding(
        config, "CE-2",
        f"Both incidents share {anchors[0].display}, but they ask for payment to different handles "
        f"({shown_a} vs {shown_b}).",
        "The same contact point paired with different payment destinations may be a reused or recycled "
        "identifier rather than one operation.",
        refs,
    )]


# ---------------------------------------------------------------------------------------------
# CE-3  benign-context identifier (HIGH)
# ---------------------------------------------------------------------------------------------

def ce3_benign_context_identifier(ctx: PairContext, config: dict, public: PublicIdentifiers | None = None) -> list[Finding]:
    public = public or get_public_identifiers()
    reasons: list[str] = []
    refs: list[dict] = []
    legit_ids = sorted(i for i in (ctx.incident_a, ctx.incident_b) if ctx.legitimate.get(i))
    for s in ctx.shared:
        entry = public.lookup(s.type, s.canonical)
        if entry:
            reasons.append(f"{s.display} is a public identifier ({entry['description']})")
            refs.extend(s.evidence_refs)
        elif legit_ids:
            reasons.append(f"{s.display} also appears in an incident labelled legitimate "
                           f"(INC-{legit_ids[0]:04d})")
            refs.extend(s.evidence_refs)
    if not reasons:
        return []
    return [_finding(
        config, "CE-3",
        "The shared identifier is used in a benign context: " + "; ".join(reasons) + ".",
        "Genuine notices and scam calls can both cite an official identifier, so seeing it twice says nothing "
        "about a common origin. The match is disputed until an analyst decides.",
        refs,
    )]


# ---------------------------------------------------------------------------------------------
# CE-4  weak entity extraction (MEDIUM, minimal)
# ---------------------------------------------------------------------------------------------

def ce4_weak_entity_extraction(ctx: PairContext, config: dict) -> list[Finding]:
    p = _rule_cfg(config, "CE-4")["params"]
    weak = [s for s in ctx.shared if s.min_extraction_confidence < p["min_extraction_confidence"]]
    if not weak:
        return []
    return [_finding(
        config, "CE-4",
        f"The shared identifier {weak[0].display} was extracted with low confidence "
        f"({weak[0].min_extraction_confidence:.2f}).",
        "A shaky extraction (partial number, truncated domain) can create a false match.",
        list(weak[0].evidence_refs),
    )]


# ---------------------------------------------------------------------------------------------
# CE-5  inconsistent impersonation (MEDIUM)
# ---------------------------------------------------------------------------------------------

def ce5_inconsistent_impersonation(ctx: PairContext, config: dict) -> list[Finding]:
    a, b = ctx.fp_a.institution_class, ctx.fp_b.institution_class
    if "UNKNOWN" in (a, b) or a == b:
        return []
    refs = _stage_refs(ctx, {"AUTHORITY"})
    return [_finding(
        config, "CE-5",
        f"The incidents claim different institutions ({a.replace('_', ' ').title()} vs {b.replace('_', ' ').title()}).",
        "One group can impersonate several institutions, but a different claimed institution makes a common "
        "origin less likely.",
        refs,
    )]


# ---------------------------------------------------------------------------------------------
# CE-7  language difference (LOW, context only)
# ---------------------------------------------------------------------------------------------

def ce7_language_difference(ctx: PairContext, config: dict) -> list[Finding]:
    a, b = ctx.fp_a.language, ctx.fp_b.language
    if not a or not b or a == b:
        return []
    return [_finding(
        config, "CE-7",
        f"The incidents are in different languages ({a} vs {b}).",
        "Recorded as context only: campaigns target many languages, so this is not a contradiction.",
        [],
    )]


RULES = [ce1_incompatible_chronology, ce2_different_payment_destination, ce3_benign_context_identifier,
         ce4_weak_entity_extraction, ce5_inconsistent_impersonation, ce7_language_difference]


def evaluate_pair(ctx: PairContext, config: dict | None = None, public: PublicIdentifiers | None = None) -> list[Finding]:
    """Run every implemented rule on one pair. Deterministic; order follows rule ids."""
    config = config or load_config()
    findings: list[Finding] = []
    for rule in RULES:
        findings.extend(rule(ctx, config, public) if rule is ce3_benign_context_identifier else rule(ctx, config))
    return findings


def adjusted_confidence(base: float, findings: list[Finding]) -> float:
    """adjusted_confidence = clip(base_confidence + sum of impacts, 0, 1)."""
    return max(0.0, min(1.0, base + sum(f.confidence_impact for f in findings)))


def has_high_severity(findings: list[Finding]) -> bool:
    return any(f.severity == "HIGH" for f in findings)
