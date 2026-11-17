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
    # --- Counter-evidence scenarios (blueprint Appendix B 11 and 12, plus conflicting payment destinations) ---
    IncidentCreate(                       # CE-3: shares the PUBLIC helpline 1930 with the genuine bank notice (seed 3)
        title="Customs call that cites the public cybercrime helpline",
        source_channel="call",
        language="en",
        scenario_id="scenario_05_public_helpline",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Caller: This is Mumbai Customs. Pay the clearance fee to clearance55@oksbi.\nVictim: Is this real?\nCaller: Yes, you can verify it on helpline 1930.",
            provenance="seed:scenario_05",
        )],
    ),
    IncidentCreate(                       # CE-1: forward script ...
        title="Chronology check A: forward script",
        source_channel="call",
        language="en",
        scenario_id="scenario_06_chronology_forward",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Caller: This is Inspector Kulkarni from the Cyber Crime Cell.\nCaller: Do not tell anyone and stay on the video call.\nCaller: Act within 20 minutes.\nCaller: Transfer the security deposit to settlement31@ybl.",
            provenance="seed:scenario_06",
        )],
    ),
    IncidentCreate(                       # CE-1: ... and the same tactics in the opposite order, same payment handle
        title="Chronology check B: reversed script",
        source_channel="call",
        language="en",
        scenario_id="scenario_07_chronology_reversed",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Caller: Transfer the security deposit to settlement31@ybl.\nCaller: Act within 20 minutes.\nCaller: Do not tell anyone and stay on the video call.\nCaller: This is Inspector Kulkarni from the Cyber Crime Cell.",
            provenance="seed:scenario_07",
        )],
    ),
    IncidentCreate(                       # CE-2: same callback number ...
        title="Payment check A: callback number, first payment handle",
        source_channel="call",
        language="en",
        scenario_id="scenario_08_payment_a",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Caller: This is Officer Rathod from the Customs Department. Call me back on +91 98765 11111.\nCaller: Transfer the clearance fee to alpha11@okaxis.",
            provenance="seed:scenario_08",
        )],
    ),
    IncidentCreate(                       # CE-2: ... but a different payment destination
        title="Payment check B: same callback number, different payment handle",
        source_channel="call",
        language="en",
        scenario_id="scenario_09_payment_b",
        evidence=[EvidenceCreate(
            type="transcript",
            text="Caller: This is Officer Rathod from the Customs Department. Call me back on +91 98765 11111.\nCaller: Transfer the clearance fee to beta22@oksbi.",
            provenance="seed:scenario_09",
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
