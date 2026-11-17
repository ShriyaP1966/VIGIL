import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.models.models import Association
from backend.app.schemas.schemas import IncidentCreate, EvidenceCreate
from backend.app.services.incident_service import create_incident, run_incident_analysis


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def test_invariant_i1_exact_observed_match(test_db):
    """
    Safety Invariant I1:
    An OBSERVED_MATCH can exist only if the normalised identifiers are exactly equal.
    """
    # Incident 1 with a specific UPI handle
    inc1 = create_incident(test_db, IncidentCreate(
        title="Digital Arrest Scam Call",
        source_channel="call",
        language="hi-Latn",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Main CBI officer bol raha hoon. Pay verification fee to verify-cbi@okhdfcbank immediately or face FIR."
        )]
    ))
    run_incident_analysis(test_db, inc1.id)

    # Incident 2 sharing the EXACT SAME UPI handle
    inc2 = create_incident(test_db, IncidentCreate(
        title="Customs Parcel Threat",
        source_channel="call",
        language="en",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Your parcel contains contraband. Send security deposit to verify-cbi@okhdfcbank within 30 minutes."
        )]
    ))
    run_incident_analysis(test_db, inc2.id)

    # Verify association was created
    assocs = test_db.query(Association).all()
    assert len(assocs) == 1
    assoc = assocs[0]
    assert assoc.status == "OBSERVED_MATCH"
    assert assoc.match_type == "EXACT_IDENTIFIER"
    assert assoc.incident_a_id == min(inc1.id, inc2.id)
    assert assoc.incident_b_id == max(inc1.id, inc2.id)

    # Incident 3 with a DIFFERENT UPI handle
    inc3 = create_incident(test_db, IncidentCreate(
        title="Unrelated Bank Phishing",
        source_channel="sms",
        language="en",
        evidence=[EvidenceCreate(
            type="message",
            text="Update your PAN at different-account@icici or card blocked."
        )]
    ))
    run_incident_analysis(test_db, inc3.id)

    # Verify NO new association formed for inc3
    assocs_inc3 = test_db.query(Association).filter(
        (Association.incident_a_id == inc3.id) | (Association.incident_b_id == inc3.id)
    ).all()
    assert len(assocs_inc3) == 0


def test_invariant_i2_no_spurious_observed_match(test_db):
    """
    Safety Invariant I2:
    No ML or heuristic output can create OBSERVED_MATCH without exact identifier equality.
    """
    inc1 = create_incident(test_db, IncidentCreate(
        title="Incident Alpha",
        evidence=[EvidenceCreate(text="Call from Cyber Police Mumbai regarding your passport.")]
    ))
    run_incident_analysis(test_db, inc1.id)

    inc2 = create_incident(test_db, IncidentCreate(
        title="Incident Beta",
        evidence=[EvidenceCreate(text="Notice from Cyber Crime Cell Delhi regarding your account.")]
    ))
    run_incident_analysis(test_db, inc2.id)

    # No shared exact phone/UPI/domain -> No OBSERVED_MATCH allowed
    assocs = test_db.query(Association).filter(Association.status == "OBSERVED_MATCH").all()
    assert len(assocs) == 0
