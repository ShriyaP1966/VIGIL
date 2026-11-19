"""Isolated replay of synthetic incidents through the REAL pipeline (blueprint §8, §9 Scenario Lab).

Every call builds its own throwaway in-memory SQLite database, ingests the records one by one through
`create_incident` and `run_incident_analysis` (the same services the API uses), reads the resulting
associations and campaign hypotheses back, and discards the database. It never touches the application's
database, makes no network call and needs no API key. Used by the evaluation harness (E3, E4) and by the
Scenario Lab API.

`candidates=False` and `counter_evidence=False` switch the fingerprint candidates and the counter-evidence
engine off for ablations. A run is deterministic: same records in, same result out.
"""

from __future__ import annotations

import json
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models import models  # noqa: F401  (register tables)
from backend.app.models.models import Analysis, Association, Campaign, CampaignMember, Entity, TacticEvent
from backend.app.schemas.schemas import EvidenceCreate, IncidentCreate
from backend.app.services import incident_service
from backend.app.services.incident_service import create_incident, run_incident_analysis

NO_CANDIDATES = 2.0          # playbook similarity never reaches this, so no candidate is created


@dataclass(frozen=True)
class Edge:
    """One association between two incidents, identified by the records' own incident ids."""
    a: str
    b: str
    status: str
    match_type: str
    shared: tuple[str, ...]            # "TYPE:canonical" of the exactly shared identifiers
    confidence: float
    similarity: float | None


@dataclass
class ReplayResult:
    edges: list[Edge] = field(default_factory=list)
    campaigns: list[dict] = field(default_factory=list)       # {members, confidence, status, bases}
    labels: dict[str, list[str]] = field(default_factory=dict)   # record id -> distinct tactic labels
    risk: dict[str, dict] = field(default_factory=dict)       # record id -> {score, band}
    injection: dict[str, list[str]] = field(default_factory=dict)   # record id -> injection rule ids that fired


def _incident_payload(rec: dict) -> IncidentCreate:
    turns = [{"speaker": u["speaker"], "text": u["text"], "t_start_sec": u.get("t_start_sec")}
             for u in rec["utterances"]]
    text = "\n".join(f"{u['speaker'].capitalize()}: {u['text']}" for u in rec["utterances"])
    return IncidentCreate(
        title=f"{rec['scenario_type']} {rec['incident_id']}",
        source_channel=rec["source_channel"],
        language=rec["language"],
        evidence=[EvidenceCreate(
            type="transcript" if rec["source_channel"] == "call" else "message",
            text=text, speaker_turns=turns, provenance="replay",
            timestamp=datetime.fromisoformat(rec["timestamp"]),
        )],
    )


def replay_records(records: list[dict], *, candidates: bool = True, counter_evidence: bool = True,
                   t_candidate: float | None = None) -> ReplayResult:
    """Run `records` (generator format) through the pipeline in an isolated in-memory database.
    `t_candidate` overrides the candidate threshold for this run only (used by the post-hoc tuning experiment);
    the default is the application's 0.75."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        with ExitStack() as stack:
            if not candidates:
                stack.enter_context(mock.patch.object(incident_service.settings, "T_CANDIDATE", NO_CANDIDATES))
            elif t_candidate is not None:
                stack.enter_context(mock.patch.object(incident_service.settings, "T_CANDIDATE", t_candidate))
            if not counter_evidence:
                stack.enter_context(mock.patch.object(incident_service, "evaluate_incident_associations",
                                                      lambda db, incident_id: False))
            db_id: dict[str, int] = {}
            for rec in sorted(records, key=lambda r: (r["timestamp"], r["incident_id"])):
                incident = create_incident(session, _incident_payload(rec))
                db_id[rec["incident_id"]] = incident.id
                run_incident_analysis(session, incident.id)
            return _read_back(session, db_id)
    finally:
        session.close()
        engine.dispose()


def _read_back(db, db_id: dict[str, int]) -> ReplayResult:
    rec_of = {v: k for k, v in db_id.items()}
    entities = {e.id: f"{e.type}:{e.canonical_value}" for e in db.query(Entity).all()}
    result = ReplayResult()
    for a in db.query(Association).order_by(Association.id):
        shared = tuple(sorted(entities[i] for i in json.loads(a.shared_entity_ids_json or "[]") if i in entities))
        x, y = sorted((rec_of[a.incident_a_id], rec_of[a.incident_b_id]))
        result.edges.append(Edge(x, y, a.status, a.match_type, shared, a.adjusted_confidence, a.similarity))
    for c in db.query(Campaign).order_by(Campaign.id):
        members = db.query(CampaignMember).filter(CampaignMember.campaign_id == c.id).all()
        result.campaigns.append({
            "members": sorted(rec_of[m.incident_id] for m in members), "confidence": c.confidence,
            "status": c.status, "bases": sorted({m.membership_basis for m in members}),
        })
    for rid, iid in db_id.items():
        result.labels[rid] = sorted({e.label for e in db.query(TacticEvent).filter(TacticEvent.incident_id == iid)})
    latest: dict[int, Analysis] = {}
    for an in db.query(Analysis).order_by(Analysis.id):
        latest[an.incident_id] = an
    for rid, iid in db_id.items():
        if iid in latest:
            result.risk[rid] = {"score": latest[iid].risk_score, "band": latest[iid].risk_band}
            result.injection[rid] = json.loads(latest[iid].injection_flags_json or "[]")
    return result
