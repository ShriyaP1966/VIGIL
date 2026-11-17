#!/usr/bin/env python3
"""
Seed script for the VIGIL Phase 1 vertical slice (blueprint §15).

Creates 3 synthetic incidents:
- Incident 1: digital-arrest style call (mentions UPI 'verify-cbi@okhdfcbank')
- Incident 2: customs-parcel style call (mentions the exact same UPI handle)
- Incident 3: genuine bank notification (unrelated negative control)

Expected: one OBSERVED_MATCH between incidents 1 and 2; incident 3 stays unlinked.
All text is synthetic. `seed_session` is reused by scripts/export_static_demo.py.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.core.database import SessionLocal, engine, Base  # noqa: E402
from backend.app.schemas.schemas import IncidentCreate, EvidenceCreate  # noqa: E402
from backend.app.services.incident_service import create_incident, run_incident_analysis  # noqa: E402
from backend.app.models.models import Association  # noqa: E402

SEED_INCIDENTS = [
    IncidentCreate(
        title="Digital Arrest Threat — CBI Officer Impersonation",
        source_channel="call",
        language="hi-Latn",
        scenario_id="scenario_01_digital_arrest",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Main CBI officer Rajesh Sharma bol raha hoon. Aapke Aadhaar card par illegal parcel Mumbai customs ne pakda hai. Is parcel mein drugs aur money laundering ke documents hain. Agar aap turant arrest warrant se bachna chahte hain to apni verification deposit 50000 rupees verify-cbi@okhdfcbank par transfer kijiye. Kisi ko mat batana, aap video call surveillance par hain.",
            provenance="seed:scenario_01",
        )],
    ),
    IncidentCreate(
        title="Customs Contraband Parcel Demand",
        source_channel="call",
        language="en",
        scenario_id="scenario_02_customs_parcel",
        evidence=[EvidenceCreate(
            type="transcript",
            text="This is Mumbai Customs Department. A package registered in your name contains counterfeit currency and passport copies. An FIR has been registered. You are directed to transfer clearance charges immediately to verify-cbi@okhdfcbank within 30 minutes.",
            provenance="seed:scenario_02",
        )],
    ),
    IncidentCreate(
        title="HDFC Official Branch Alert",
        source_channel="sms",
        language="en",
        scenario_id="scenario_03_legit_bank",
        evidence=[EvidenceCreate(
            type="message",
            text="Dear Customer, your monthly bank statement has been dispatched to your registered email address. For inquiries, visit your nearest bank branch with original photo ID or call official national helpline 1930. Never share passwords or PINs.",
            provenance="seed:scenario_03",
        )],
    ),
]


def seed_session(db, verbose: bool = False) -> list[int]:
    """Create the three seed incidents in the given session and return their ids."""
    ids = []
    for payload in SEED_INCIDENTS:
        inc = create_incident(db, payload)
        run_incident_analysis(db, inc.id)
        ids.append(inc.id)
        if verbose:
            print(f"  -> Created Incident #{inc.id}: {payload.title}")
    return ids


def seed():
    print("Initializing SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Association).filter(Association.status == "OBSERVED_MATCH").all()
        if existing:
            print(f"Database already contains {len(existing)} OBSERVED_MATCH association(s). Reseed skipped.")
            return

        print("Creating synthetic incidents...")
        seed_session(db, verbose=True)

        assocs = db.query(Association).all()
        print("\nVerification Results:")
        print(f"  Total associations created: {len(assocs)}")
        for a in assocs:
            print(f"  - Association #{a.id} [{a.status}]: INC-{a.incident_a_id} <-> INC-{a.incident_b_id} "
                  f"(confidence: {a.adjusted_confidence})")
            print(f"    Reason: {a.explanation}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
