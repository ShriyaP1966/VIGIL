#!/usr/bin/env python3
"""
Seed script for VIGIL Phase 1 Vertical Slice (§15).
Creates 3 synthetic benchmark incidents:
- Incident 1: Digital arrest scam call (shares UPI 'verify-cbi@okhdfcbank')
- Incident 2: Customs parcel scam call (shares exact same UPI 'verify-cbi@okhdfcbank')
- Incident 3: Legitimate bank alert (unrelated negative control)
Produces:
- 1 OBSERVED_MATCH association linking Incident 1 and Incident 2
- Incident 3 remains isolated
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


def seed():
    print("Initializing SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_assocs = db.query(Association).filter(Association.status == "OBSERVED_MATCH").all()
        if existing_assocs:
            print(f"Database already contains {len(existing_assocs)} OBSERVED_MATCH association(s). Reseed skipped.")
            return

        print("Creating synthetic Incident 1: Digital Arrest Call (CBI Impersonation)...")
        inc1 = create_incident(db, IncidentCreate(
            title="Digital Arrest Threat — CBI Officer Impersonation",
            source_channel="call",
            language="hi-Latn",
            scenario_id="scenario_01_digital_arrest",
            evidence=[EvidenceCreate(
                type="transcript",
                text="Main CBI officer Rajesh Sharma bol raha hoon. Aapke Aadhaar card par illegal parcel Mumbai customs ne pakda hai. Is parcel mein drugs aur money laundering ke documents hain. Agar aap turant arrest warrant se bachna chahte hain to apni verification deposit 50000 rupees verify-cbi@okhdfcbank par transfer kijiye. Kisi ko mat batana, aap video call surveillance par hain.",
                provenance="seed:scenario_01"
            )]
        ))
        run_incident_analysis(db, inc1.id)
        print(f"  -> Created Incident #{inc1.id}")

        print("Creating synthetic Incident 2: Customs Contraband Parcel Demand (Same UPI)...")
        inc2 = create_incident(db, IncidentCreate(
            title="Customs Contraband Parcel Demand",
            source_channel="call",
            language="en",
            scenario_id="scenario_02_customs_parcel",
            evidence=[EvidenceCreate(
                type="transcript",
                text="This is Mumbai Customs Department. A package registered in your name contains counterfeit currency and passport copies. An FIR has been registered. You are directed to transfer clearance charges immediately to verify-cbi@okhdfcbank within 30 minutes.",
                provenance="seed:scenario_02"
            )]
        ))
        run_incident_analysis(db, inc2.id)
        print(f"  -> Created Incident #{inc2.id}")

        print("Creating synthetic Incident 3: Legitimate Bank Notification (Negative Control)...")
        inc3 = create_incident(db, IncidentCreate(
            title="HDFC Official Branch Alert",
            source_channel="sms",
            language="en",
            scenario_id="scenario_03_legit_bank",
            evidence=[EvidenceCreate(
                type="message",
                text="Dear Customer, your monthly bank statement has been dispatched to your registered email address. For inquiries, visit your nearest bank branch with original photo ID or call official national helpline 1930. Never share passwords or PINs.",
                provenance="seed:scenario_03"
            )]
        ))
        run_incident_analysis(db, inc3.id)
        print(f"  -> Created Incident #{inc3.id}")

        # Verify Associations
        assocs = db.query(Association).all()
        print("\nVerification Results:")
        print(f"  Total Associations Created: {len(assocs)}")
        for a in assocs:
            print(f"  - Association #{a.id} [{a.status}]: INC-{a.incident_a_id} <-> INC-{a.incident_b_id} (Confidence: {a.adjusted_confidence})")
            print(f"    Reason: {a.explanation}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
