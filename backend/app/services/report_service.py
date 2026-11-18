"""Structured incident report (blueprint §9, §12.4): observed facts, model inferences, analyst actions,
counter-evidence and limitations kept apart, exportable as JSON or CSV.

The report is deterministic (no generation timestamp), built only from stored data, and never contains a secret:
evidence text was redacted before storage and identifiers appear in their masked display form. Untrusted text
(excerpts) is exported as data; the CSV writer neutralises spreadsheet formulas.
"""

from __future__ import annotations

import csv
import io
import json

from sqlalchemy.orm import Session

from ai_engine.extraction.tactics import STAGE_OF_LABEL
from backend.app.models.models import (
    Analysis, Association, Campaign, CampaignMember, CounterEvidence, Entity, Evidence, Incident, Mention,
    Review, RiskContribution, TacticEvent, Utterance,
)

REPORT_VERSION = "report@1.0"
EXCERPT_CHARS = 200

LIMITATIONS = [
    "All data is synthetic. Nothing in this report is evidence about a real person or organisation.",
    "A campaign hypothesis groups incidents that may be related. It is not an established finding and does not "
    "attribute activity to any person or organisation; an analyst must review it.",
    "An OBSERVED_MATCH means the same normalised identifier appears in two evidence records. It is an observation, "
    "not proof that one actor is behind both.",
    "A CANDIDATE_ASSOCIATION means a similar script (playbook), with no shared identifier. The fingerprint recognises "
    "a script family, not a specific group, and it cannot tell two incidents of one script apart.",
    "The risk score is an experimental heuristic with a-priori weights, uncalibrated; it is not a probability.",
    "Tactic labels come from a hand-written keyword lexicon. It matches wording, not intent, so quoted or reported "
    "scam wording can be labelled as a scam tactic.",
    "Counter-evidence rules CE-6 and CE-8 are not implemented, and rule coverage of benign identifiers is a small "
    "starter list.",
    "Secrets (OTP, PIN, CVV, password, card, Aadhaar) are removed at ingestion on a best-effort basis; only counts "
    "of removals are kept.",
]


def _shared_identifiers(db: Session, assoc: Association) -> list[dict]:
    ids = json.loads(assoc.shared_entity_ids_json or "[]")
    rows = db.query(Entity).filter(Entity.id.in_(ids)).order_by(Entity.id).all() if ids else []
    return [{"type": e.type, "display_value": e.display_value} for e in rows]


def _association_row(db: Session, assoc: Association, incident_id: int) -> dict:
    other_id = assoc.incident_b_id if assoc.incident_a_id == incident_id else assoc.incident_a_id
    other = db.query(Incident).filter(Incident.id == other_id).first()
    return {
        "association_id": assoc.id, "other_incident_id": other_id, "other_incident_title": other.title if other else None,
        "status": assoc.status, "match_type": assoc.match_type,
        "confidence": round(assoc.adjusted_confidence, 4), "base_confidence": round(assoc.base_confidence, 4),
        "shared_identifiers": _shared_identifiers(db, assoc), "explanation": assoc.explanation,
        "algorithm_version": assoc.algorithm_version,
    }


def build_report(db: Session, incident_id: int) -> dict:
    """Raises LookupError if the incident does not exist."""
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if inc is None:
        raise LookupError("Incident not found")

    evidence = db.query(Evidence).filter(Evidence.incident_id == incident_id).order_by(Evidence.id).all()
    mentions = (
        db.query(Mention, Entity).join(Entity, Mention.entity_id == Entity.id)
        .join(Evidence, Mention.evidence_id == Evidence.id).filter(Evidence.incident_id == incident_id).all()
    )
    identifiers: dict[tuple[str, str], int] = {}
    for _m, ent in mentions:
        key = (ent.type, ent.display_value)
        identifiers[key] = identifiers.get(key, 0) + 1

    assocs = (
        db.query(Association)
        .filter((Association.incident_a_id == incident_id) | (Association.incident_b_id == incident_id))
        .order_by(Association.id).all()
    )
    rows = [_association_row(db, a, incident_id) for a in assocs]
    assoc_ids = {a.id for a in assocs}
    members = db.query(CampaignMember).filter(CampaignMember.incident_id == incident_id).all()
    campaigns = db.query(Campaign).filter(Campaign.id.in_([m.campaign_id for m in members])).order_by(Campaign.id).all() \
        if members else []

    # model inferences: tactics, stages, risk
    events = (
        db.query(TacticEvent, Utterance).join(Utterance, TacticEvent.utterance_id == Utterance.id)
        .filter(TacticEvent.incident_id == incident_id).order_by(TacticEvent.id).all()
    )
    tactics: dict[str, dict] = {}
    for ev, utt in events:
        start, end = (int(x) for x in ev.evidence_span.split(":"))
        t = tactics.setdefault(ev.label, {"label": ev.label, "stage": STAGE_OF_LABEL.get(ev.label), "count": 0,
                                          "max_confidence": 0.0, "excerpts": []})
        t["count"] += 1
        t["max_confidence"] = max(t["max_confidence"], round(ev.confidence, 4))
        if len(t["excerpts"]) < 3:
            t["excerpts"].append({"utterance_idx": utt.idx, "text": utt.text[start:end][:EXCERPT_CHARS]})
    analysis = db.query(Analysis).filter(Analysis.incident_id == incident_id).order_by(Analysis.id.desc()).first()
    risk = None
    fingerprint = {}
    if analysis:
        contributions = db.query(RiskContribution).filter(RiskContribution.analysis_id == analysis.id) \
            .order_by(RiskContribution.id).all()
        risk = {
            "score": analysis.risk_score, "band": analysis.risk_band, "version": analysis.risk_version,
            "note": "Experimental heuristic, not a probability. Contributions sum exactly to the score.",
            "injection_flags": json.loads(analysis.injection_flags_json or "[]"),
            "contributions": [{"factor": c.factor, "effect": c.effect, "contribution": c.contribution,
                               "explanation": c.explanation, "rule_version": c.rule_version} for c in contributions],
        }
        fingerprint = json.loads(analysis.fingerprint_json or "{}")

    # analyst actions: reviews of this incident's associations and of the hypotheses it belongs to
    reviews = []
    for r in db.query(Review).order_by(Review.id).all():
        if (r.target_type == "association" and r.target_id in assoc_ids) or \
                (r.target_type == "campaign" and r.target_id in {c.id for c in campaigns}):
            reviews.append({"target_type": r.target_type, "target_id": r.target_id, "decision": r.decision,
                            "note": r.note, "previous_status": r.previous_status, "new_status": r.new_status,
                            "recorded_at": r.created_at.isoformat() if r.created_at else None})

    findings = []
    if assoc_ids:
        for ce in db.query(CounterEvidence).filter(CounterEvidence.association_id.in_(assoc_ids)) \
                .order_by(CounterEvidence.association_id, CounterEvidence.id):
            findings.append({"association_id": ce.association_id, "rule_id": ce.rule_id, "kind": ce.kind,
                             "severity": ce.severity, "observation": ce.observation, "explanation": ce.explanation,
                             "confidence_impact": ce.confidence_impact, "rule_version": ce.rule_version})

    return {
        "report_version": REPORT_VERSION,
        "synthetic": bool(inc.is_synthetic),
        "incident": {"id": inc.id, "title": inc.title, "source_channel": inc.source_channel, "language": inc.language,
                     "status": inc.status, "created_at": inc.created_at.isoformat() if inc.created_at else None},
        "observed_facts": {
            "evidence": [{"id": e.id, "type": e.type, "sha256": e.sha256, "provenance": e.provenance,
                          "characters": len(e.original_text)} for e in evidence],
            "identifiers": [{"type": t, "display_value": v, "mentions": n} for (t, v), n in sorted(identifiers.items())],
            "observed_matches": [r for r in rows if r["status"] == "OBSERVED_MATCH"],
        },
        "model_inferences": {
            "stage_sequence": fingerprint.get("stage_sequence", []),
            "institution_class": fingerprint.get("institution_class"),
            "payment_channel": fingerprint.get("payment_channel"),
            "tactics": sorted(tactics.values(), key=lambda t: t["label"]),
            "risk": risk,
            "behavioural_candidates": [r for r in rows if r["status"] == "CANDIDATE_ASSOCIATION"],
            "campaign_hypotheses": [{"id": c.id, "title": c.hypothesis_title, "status": c.status,
                                     "confidence": round(c.confidence, 4)} for c in campaigns],
        },
        "analyst_actions": reviews,
        "counter_evidence": {
            "findings": findings,
            "disputed_or_rejected_links": [r for r in rows
                                           if r["status"] in ("DISPUTED_ASSOCIATION", "REJECTED_ASSOCIATION")],
        },
        "limitations": LIMITATIONS,
    }


# ---------------------------------------------------------------------------------------------
# CSV (long format: section, record, field, value)
# ---------------------------------------------------------------------------------------------

def _safe(value) -> str:
    """Neutralise spreadsheet formulas: untrusted text may start with = + - @ (or a tab / carriage return)."""
    text = "" if value is None else (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def to_csv(report: dict) -> str:
    """Flatten the report to rows (section, record, field, value). A list of records becomes one section with a
    record index per item (nested lists extend the index, e.g. 2.0); scalars and lists of scalars are one field."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["section", "record", "field", "value"])

    def walk(path: str, node, record: str = "0") -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                if isinstance(val, dict):
                    walk(f"{path}.{key}", val, record)
                elif isinstance(val, list) and val and all(isinstance(x, dict) for x in val):
                    for i, item in enumerate(val):
                        walk(f"{path}.{key}", item, str(i) if record == "0" else f"{record}.{i}")
                else:
                    writer.writerow([path, record, key, _safe(val)])
        elif isinstance(node, list):
            for i, item in enumerate(node):
                if isinstance(item, dict):
                    walk(path, item, str(i))
                else:
                    writer.writerow([path, str(i), "value", _safe(item)])
        else:
            writer.writerow([path, record, "value", _safe(node)])

    writer.writerow(["report", "0", "report_version", report["report_version"]])
    writer.writerow(["report", "0", "synthetic", str(report["synthetic"]).lower()])
    for section in ("incident", "observed_facts", "model_inferences", "analyst_actions", "counter_evidence",
                    "limitations"):
        walk(section, report[section])
    return out.getvalue()
