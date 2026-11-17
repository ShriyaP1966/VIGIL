"""Synthetic seed incidents for the Phase 1 vertical slice (blueprint §15).

Three synthetic incidents: two share the exact UPI handle 'verify-cbi@okhdfcbank' (expect one
OBSERVED_MATCH), the third is a genuine bank notification that must stay unlinked.
Used by scripts/seed_demo.py, scripts/export_static_demo.py and optional startup seeding
(SEED_ON_START=true) for hosts with an ephemeral disk such as Render's free tier.
"""

from sqlalchemy.orm import Session

from backend.app.schemas.schemas import IncidentCreate, EvidenceCreate
from backend.app.services.incident_service import create_incident, run_incident_analysis

SEED_INCIDENTS = [
    IncidentCreate(
        title="Digital Arrest Threat — CBI Officer Impersonation",
        source_channel="call",
        language="hi-Latn",
        scenario_id="scenario_01_digital_arrest",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Caller: Main CBI officer Rajesh Sharma bol raha hoon. Aapke Aadhaar card par illegal parcel Mumbai customs ne pakda hai. Is parcel mein drugs aur money laundering ke documents hain.\nVictim: Lekin maine kuch galat nahi kiya.\nCaller: Agar aap turant arrest warrant se bachna chahte hain to apni verification deposit 50000 rupees verify-cbi@okhdfcbank par transfer kijiye. Kisi ko mat batana, aap video call surveillance par hain.",
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
            text="Caller: This is Mumbai Customs Department. A package registered in your name contains counterfeit currency and passport copies. An FIR has been registered.\nVictim: What? I did not send any package.\nCaller: You are directed to transfer clearance charges immediately to verify-cbi@okhdfcbank within 30 minutes.",
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
    IncidentCreate(
        title="CBI-style call with rotated identifiers",
        source_channel="call",
        language="en",
        scenario_id="scenario_04_rotated_identifiers",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Caller: This is Officer Anil Verma from the CBI cyber division. Your SIM card is linked to a money laundering case.\nVictim: I did not do anything.\nCaller: You will be arrested within 30 minutes. Do not tell anyone and stay on the video call.\nCaller: Transfer a refundable deposit to clearance47@okicici.",
            provenance="seed:scenario_04",
        )],
    ),
]


def seed_session(db: Session, verbose: bool = False) -> list[int]:
    """Create the seed incidents in the given session, run analysis, and return their ids."""
    ids = []
    for payload in SEED_INCIDENTS:
        inc = create_incident(db, payload)
        run_incident_analysis(db, inc.id)
        ids.append(inc.id)
        if verbose:
            print(f"  -> Created Incident #{inc.id}: {payload.title}")
    return ids
