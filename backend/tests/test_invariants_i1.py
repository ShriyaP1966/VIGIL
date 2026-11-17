"""Safety invariants I1/I2: OBSERVED_MATCH only for exactly equal normalised identifiers."""
import json
import pytest

from backend.app.models.models import Association, Entity, Mention, Evidence
from backend.app.schemas.schemas import IncidentCreate, EvidenceCreate
from backend.app.services.association_service import is_exact_identifier_match
from backend.app.services.incident_service import create_incident, run_incident_analysis


@pytest.fixture
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _incident(db, title, text):
    inc = create_incident(db, IncidentCreate(title=title, evidence=[EvidenceCreate(text=text)]))
    run_incident_analysis(db, inc.id)
    return inc


def _observed(db):
    return db.query(Association).filter(Association.status == "OBSERVED_MATCH").all()


def assert_i1_holds(db):
    """Property check over the whole database: every OBSERVED_MATCH is backed by one entity row
    that is mentioned in evidence of BOTH incidents (exact canonical equality), and nothing else
    creates observed matches."""
    for assoc in _observed(db):
        assert assoc.match_type == "EXACT_IDENTIFIER"
        shared = json.loads(assoc.shared_entity_ids_json)
        assert shared, "OBSERVED_MATCH without a shared entity violates I1"
        for ent_id in shared:
            for inc_id in (assoc.incident_a_id, assoc.incident_b_id):
                hits = (
                    db.query(Mention)
                    .join(Evidence, Mention.evidence_id == Evidence.id)
                    .filter(Mention.entity_id == ent_id, Evidence.incident_id == inc_id)
                    .count()
                )
                assert hits >= 1, f"entity {ent_id} not mentioned in incident {inc_id}"
        # I5: evidence references + explanation
        assert json.loads(assoc.supporting_evidence_json)
        assert assoc.explanation


@pytest.mark.parametrize("text_a,text_b", [
    # near-miss UPI handles must NOT match (no fuzzy matching in OBSERVED_MATCH)
    ("Pay to verify-cbi@okhdfcbank", "Pay to verify-cbi@okhdfcbank2"),
    ("Pay to verify-cbi@okhdfcbank", "Pay to verify_cbi@okhdfcbank"),
    ("Pay to verify-cbi@okhdfcbank", "Pay to verify-cb@okhdfcbank"),
    # same user, different bank handle
    ("Pay to ramesh@okaxis", "Pay to ramesh@oksbi"),
    # phone numbers differing by one digit
    ("Call +91 98765 43210", "Call +91 98765 43211"),
    # different path on the same host is a different URL, but the host (DOMAIN) is shared, tested below
])
def test_i1_near_misses_never_create_observed_match(db, text_a, text_b):
    _incident(db, "A", text_a)
    _incident(db, "B", text_b)
    assert _observed(db) == []
    assert_i1_holds(db)


@pytest.mark.parametrize("text_a,text_b", [
    ("Pay to Verify-CBI@OkHdfcBank", "Pay to verify-cbi@okhdfcbank"),            # case-insensitive UPI
    ("Call +91 98765 43210", "Call 09876543210"),                                # phone formats -> E.164
    ("Call 9876543210", "Call +91-9876543210"),
    ("Pay to verify​-cbi@okhdfcbank", "Pay to verify-cbi@okhdfcbank"),     # zero-width char evasion
    ("Visit https://www.Fake-Portal.com/pay.", "See http://fake-portal.com/pay/"),  # www/case/scheme-trailing dot
])
def test_i1_equivalent_forms_match_exactly(db, text_a, text_b):
    _incident(db, "A", text_a)
    _incident(db, "B", text_b)
    assert len(_observed(db)) == 1
    assert_i1_holds(db)


def test_shared_domain_with_different_urls_still_exact_on_domain_only(db):
    _incident(db, "A", "Open https://fake-portal.com/a")
    _incident(db, "B", "Open https://fake-portal.com/b")
    assocs = _observed(db)
    assert len(assocs) == 1
    types = {db.query(Entity).filter(Entity.id == i).one().type for i in json.loads(assocs[0].shared_entity_ids_json)}
    assert types == {"DOMAIN"}  # the full URLs differ, so URL is not a shared identifier
    assert_i1_holds(db)


def test_organisation_and_language_alone_never_link_incidents(db):
    _incident(db, "A", "This is the CBI. Your account is under review.")
    _incident(db, "B", "CBI officer here, we are calling about your parcel.")
    assert db.query(Association).count() == 0  # I2: no non-identifier route to any association in Phase 1


def test_same_incident_repeated_identifier_creates_no_self_link(db):
    _incident(db, "A", "Pay to a@okaxis, I repeat a@okaxis")
    assert db.query(Association).count() == 0


def test_is_exact_identifier_match_predicate():
    ph1 = Entity(type="PHONE", canonical_value="+919876543210", display_value="x")
    ph2 = Entity(type="PHONE", canonical_value="+919876543210", display_value="x")
    ph3 = Entity(type="PHONE", canonical_value="+919876543211", display_value="x")
    upi = Entity(type="UPI_HANDLE", canonical_value="+919876543210", display_value="x")
    org = Entity(type="ORGANISATION", canonical_value="CBI", display_value="CBI")
    assert is_exact_identifier_match(ph1, ph2)
    assert not is_exact_identifier_match(ph1, ph3)
    assert not is_exact_identifier_match(ph1, upi)          # type must match too
    assert not is_exact_identifier_match(org, org)          # organisations are never linkable
    assert not is_exact_identifier_match(ph1, None)
