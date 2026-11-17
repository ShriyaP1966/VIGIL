"""Phase 3 property and integration tests, run through the REAL pipeline on generated incidents.

Only the train and dev splits are used (never the test split), so nothing here can influence threshold choices.
Properties: I1/I2 over the whole database, decoys fail the gate, partial calls match through containment,
the engine agrees with the specification for every pair, and results do not depend on ingestion order.
"""
import json
import random
import sys
from itertools import combinations
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai_engine.fingerprint.similarity import DEFAULT_T_CANDIDATE, Fingerprint, compare
from backend.app.core.database import Base
from backend.app.models import models  # noqa: F401
from backend.app.models.models import Analysis, Association, Campaign, CampaignMember, Entity, Evidence, Incident, Mention, Review
from backend.app.schemas.schemas import EvidenceCreate, IncidentCreate
from backend.app.services.association_service import LINKABLE_TYPES
from backend.app.services.incident_service import create_incident, run_incident_analysis

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import generate_dataset as gen  # noqa: E402

DEV_TRAIN = ("train", "dev")


def fresh_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def ingest(db, records):
    """Create and analyse each record; the incident title carries the dataset incident id."""
    for r in records:
        text = "\n".join(f"{u['speaker']}: {u['text']}" for u in r["utterances"])
        inc = create_incident(db, IncidentCreate(
            title=r["incident_id"], source_channel=r["source_channel"], language=r["language"],
            evidence=[EvidenceCreate(text=text)]))
        run_incident_analysis(db, inc.id)


def records_for(rotation, seed=1, splits=DEV_TRAIN):
    return [r for r in gen.generate(seed, rotation) if r["split"] in splits]


def names(db):
    return {i.id: i.title for i in db.query(Incident)}


def snapshot(db):
    """Order-independent view of everything the engine produced, keyed by dataset incident ids."""
    t = names(db)
    assocs = sorted(
        (tuple(sorted((t[a.incident_a_id], t[a.incident_b_id]))), a.status, a.match_type,
         None if a.similarity is None else round(a.similarity, 9), round(a.adjusted_confidence, 9))
        for a in db.query(Association))
    camps = sorted(
        (tuple(sorted(t[m.incident_id] for m in c.members)), c.status,
         tuple(sorted((t[m.incident_id], m.membership_basis) for m in c.members)), round(c.confidence, 9))
        for c in db.query(Campaign))
    return assocs, camps


@pytest.fixture(scope="module", params=[0.0, 0.5, 1.0], ids=lambda r: f"rotation={r}")
def world(request):
    db = fresh_db()
    records = records_for(request.param)
    ingest(db, records)
    yield db, records
    db.close()


# ---------------------------------------------------------------------------------------------
# I1 / I2 over the whole database, with an independent oracle
# ---------------------------------------------------------------------------------------------

def test_i1_observed_matches_are_exactly_the_pairs_that_share_an_exact_identifier(world):
    db, _ = world
    by_entity = {}
    for mention, evidence, entity in (
        db.query(Mention, Evidence, Entity).join(Evidence, Mention.evidence_id == Evidence.id)
        .join(Entity, Mention.entity_id == Entity.id)
    ):
        if entity.type in LINKABLE_TYPES:
            by_entity.setdefault((entity.type, entity.canonical_value), set()).add(evidence.incident_id)
    oracle = {tuple(sorted(p)) for ids in by_entity.values() for p in combinations(sorted(ids), 2)}

    observed = {(a.incident_a_id, a.incident_b_id) for a in db.query(Association).filter(Association.status == "OBSERVED_MATCH")}
    sharing = {(a.incident_a_id, a.incident_b_id) for a in db.query(Association)
               if json.loads(a.shared_entity_ids_json)}
    assert observed == oracle == sharing                 # nothing missed, nothing invented


def test_i2_behaviour_only_links_are_never_observed_or_analyst_set(world):
    db, _ = world
    for a in db.query(Association):
        if a.match_type == "PLAYBOOK":
            assert a.status == "CANDIDATE_ASSOCIATION"
            assert json.loads(a.shared_entity_ids_json) == []
        if a.status == "OBSERVED_MATCH":
            assert a.match_type in ("EXACT_IDENTIFIER", "COMBINED") and json.loads(a.shared_entity_ids_json)
    # No reviewer acted in this run, so the engine alone produced no analyst-only status (I2/I3)
    assert db.query(Association).filter(Association.status.in_(
        ["ANALYST_VERIFIED_ASSOCIATION", "REJECTED_ASSOCIATION"])).count() == 0
    assert db.query(Review).count() == 0


def test_i5_every_association_has_evidence_and_an_explanation(world):
    db, _ = world
    for a in db.query(Association):
        assert json.loads(a.supporting_evidence_json) and a.explanation.strip()
        assert 0.0 <= a.adjusted_confidence <= 1.0


# ---------------------------------------------------------------------------------------------
# Decoys and legitimate incidents fail the gate
# ---------------------------------------------------------------------------------------------

def test_no_legitimate_incident_is_ever_linked(world):
    db, records = world
    legit_titles = {r["incident_id"] for r in records if r["scenario_type"] == "legitimate"}
    assert len(legit_titles) >= 15
    t = names(db)
    for a in db.query(Association):
        assert t[a.incident_a_id] not in legit_titles and t[a.incident_b_id] not in legit_titles


def test_same_tactics_in_reverse_chronology_fails_the_gate():
    db = fresh_db()
    forward = ("Caller: This is Inspector Rao from the Cyber Crime Cell. Your Aadhaar is linked to a money laundering case.\n"
               "Caller: You will be arrested within 30 minutes. Do not tell anyone and stay on the video call.\n"
               "Caller: Transfer the security deposit to fwd1@okaxis.")
    reverse = ("Caller: Transfer the security deposit to rev1@ybl.\n"
               "Caller: Do not tell anyone and stay on the video call.\n"
               "Caller: You will be arrested within 30 minutes.\n"
               "Caller: Your Aadhaar is linked to a money laundering case.\n"
               "Caller: This is Inspector Rao from the Cyber Crime Cell.")
    for text in (forward, reverse):
        inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(text=text)]))
        run_incident_analysis(db, inc.id)
    fps = [Fingerprint.from_json(json.loads(a.fingerprint_json)) for a in db.query(Analysis).order_by(Analysis.id)]
    assert set(fps[0].sequence) == set(fps[1].sequence) and len(fps[0].sequence) == 6      # same six tactics...
    result = compare(fps[0], fps[1])
    assert result.lcs < 3 and not result.gate_passed                                       # ...in the wrong order
    assert db.query(Association).count() == 0


def test_similar_wording_without_the_scam_script_fails_the_gate():
    db = fresh_db()
    texts = [
        "Caller: This is Inspector Rao from the Cyber Crime Cell. Your Aadhaar is linked to a money laundering case.\n"
        "Caller: You will be arrested within 30 minutes. Do not tell anyone and stay on the video call.\n"
        "Caller: Transfer the security deposit to scam1@okaxis.",
        # benign notice that borrows the vocabulary (authority, KYC, urgency word) but has no threat/isolation/demand
        "Dear customer, this is the HDFC Bank customer care team. Your KYC is pending. Please visit your nearest branch "
        "within 30 days with your ID. No payment is required.",
    ]
    for text in texts:
        inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(text=text)]))
        run_incident_analysis(db, inc.id)
    assert db.query(Association).count() == 0


# ---------------------------------------------------------------------------------------------
# Partial calls match through containment
# ---------------------------------------------------------------------------------------------

def test_partial_calls_are_contained_in_their_full_calls(world):
    db, records = world
    t = names(db)
    fingerprints = {t[a.incident_id]: Fingerprint.from_json(json.loads(a.fingerprint_json)) for a in db.query(Analysis)}
    checked = 0
    for r in records:
        if r["campaign_instance_id"] is None:
            continue
        mine = fingerprints[r["incident_id"]]
        for other_id in r["expected_associations"]:
            theirs = fingerprints[other_id]
            short, long_ = sorted([mine, theirs], key=lambda f: len(f.sequence))
            if 3 <= len(short.sequence) < len(long_.sequence) and long_.sequence[:len(short.sequence)] == short.sequence:
                res = compare(short, long_)
                assert res.lcs == len(short.sequence) and res.containment == 1.0
                assert res.lcs_sim < 1.0 and res.gate_passed          # strict similarity drops, containment keeps it alive
                checked += 1
    assert checked > 0, "the dataset should contain at least one cut-off call in this split"


# ---------------------------------------------------------------------------------------------
# The engine agrees with the specification for EVERY pair
# ---------------------------------------------------------------------------------------------

def test_engine_output_equals_the_specification_for_every_pair(world):
    db, _ = world
    latest = {}
    for a in db.query(Analysis).order_by(Analysis.id):
        latest[a.incident_id] = Fingerprint.from_json(json.loads(a.fingerprint_json))
    stored = {(a.incident_a_id, a.incident_b_id): a for a in db.query(Association)}
    expected_candidates = 0
    for a_id, b_id in combinations(sorted(latest), 2):
        res = compare(latest[a_id], latest[b_id], DEFAULT_T_CANDIDATE)
        row = stored.get((a_id, b_id))
        if res.is_candidate:
            expected_candidates += 1
            assert row is not None, f"missing association for pair {a_id}-{b_id}"
            assert row.similarity == pytest.approx(res.playbook_sim)
            assert row.status in ("CANDIDATE_ASSOCIATION", "OBSERVED_MATCH")
        elif row is not None:
            # without a candidate-level similarity the only legitimate link is an exact identifier match
            assert row.status == "OBSERVED_MATCH" and row.match_type == "EXACT_IDENTIFIER"
    assert expected_candidates == sum(1 for r in stored.values() if r.similarity is not None)


def test_hypotheses_are_consistent_with_their_links(world):
    db, _ = world
    for c in db.query(Campaign):
        ids = {m.incident_id for m in db.query(CampaignMember).filter(CampaignMember.campaign_id == c.id)}
        assert len(ids) >= 2 and c.status == "HYPOTHESIS_UNREVIEWED" and 0.0 <= c.confidence <= 1.0
        inside = [a for a in db.query(Association) if a.incident_a_id in ids and a.incident_b_id in ids
                  and a.status in ("OBSERVED_MATCH", "CANDIDATE_ASSOCIATION", "ANALYST_VERIFIED_ASSOCIATION")]
        assert c.weakest_link_association_id in [a.id for a in inside]
        assert c.confidence == pytest.approx(sum(a.adjusted_confidence for a in inside) / len(inside))
    # every incident that has a connecting link belongs to exactly one hypothesis
    linked = {i for a in db.query(Association) for i in (a.incident_a_id, a.incident_b_id)
              if a.status in ("OBSERVED_MATCH", "CANDIDATE_ASSOCIATION")}
    members = [m.incident_id for m in db.query(CampaignMember)]
    assert sorted(members) == sorted(linked) and len(members) == len(set(members))


# ---------------------------------------------------------------------------------------------
# Determinism: the result does not depend on ingestion order or on re-analysis
# ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("rotation", [0.5, 1.0])
def test_results_do_not_depend_on_ingestion_order(rotation):
    records = records_for(rotation, splits=("dev",))
    variants = {"given": list(records), "reversed": list(reversed(records)),
                "shuffled": random.Random(7).sample(records, len(records))}
    snapshots = {}
    for name, order in variants.items():
        db = fresh_db()
        ingest(db, order)
        snapshots[name] = snapshot(db)
        db.close()
    assert snapshots["given"] == snapshots["reversed"] == snapshots["shuffled"]
    assert snapshots["given"][0], "expected at least one association in the dev split"


def test_reanalysing_everything_changes_nothing():
    db = fresh_db()
    ingest(db, records_for(0.5, splits=("dev",)))
    before = snapshot(db)
    for inc in db.query(Incident).all():
        run_incident_analysis(db, inc.id)
    assert snapshot(db) == before


def test_generation_and_analysis_are_reproducible_across_runs():
    runs = []
    for _ in range(2):
        db = fresh_db()
        ingest(db, records_for(0.5, splits=("dev",)))
        runs.append(snapshot(db))
        db.close()
    assert runs[0] == runs[1]
