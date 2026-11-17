#!/usr/bin/env python3
"""
Seed script for the VIGIL Phase 1 vertical slice (blueprint §15).

Creates 3 synthetic incidents (two share a UPI handle, one genuine bank notice stays unlinked).
Data lives in backend/app/services/seed_service.py. All text is synthetic.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.core.database import SessionLocal, engine, Base  # noqa: E402
from backend.app.models.models import Association  # noqa: E402
from backend.app.services.seed_service import seed_session  # noqa: E402


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
