#!/usr/bin/env python3
"""Synthetic dataset generator v1 (blueprint §7). Everything it writes is synthetic and says so.

Slot-based templates: 6 scam campaign templates (3 digital-arrest variants, bank KYC, payment link,
courier/customs) x 12 incidents, plus 40 legitimate negatives. Seeded and deterministic. Campaign
incidents come in instances of 3; between successive incidents of one instance each identifier (phone,
UPI handle, domain, account) is replaced by a fresh synthetic one with probability `--rotation`.

Splits are by campaign template (never by paraphrase): train T1,T4 / dev T2,T5 / test T3,T6.
Decoys, the injection attacks file and the hand-written held-out set are Phase 5 / owner work.

Identifiers are synthetic by construction: phones use the widely-used example range +91 98765 xxxxx,
domains end in the reserved `.example` TLD, UPI handles use invented names. The validator re-checks this
and runs every text through the secret redactor, so no OTP/card/Aadhaar-like value can be present.

Usage:
  python scripts/generate_dataset.py --seed 1 [--rotation 0.5] [--out data/scenarios.jsonl]
  python scripts/generate_dataset.py --validate-only [--out data/scenarios.jsonl]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai_engine.extraction.tactics import CANONICAL_STAGES, TACTIC_LABELS  # noqa: E402
from ai_engine.privacy.redaction import redact_text  # noqa: E402

GENERATOR_VERSION = "gen@1.0"
DEFAULT_OUT = ROOT / "data" / "scenarios.jsonl"
MAX_BYTES = 1_000_000

TEMPLATE_SPLIT = {"T1": "train", "T4": "train", "T2": "dev", "T5": "dev", "T3": "test", "T6": "test"}
NEGATIVE_SPLIT = {"N1": "train", "N2": "train", "N3": "dev", "N4": "dev", "N5": "test", "N6": "test"}
NEGATIVE_COUNTS = {"N1": 8, "N2": 6, "N3": 7, "N4": 7, "N5": 6, "N6": 6}   # 40 in total

STAGE_LABEL = {
    "AUTH": "AUTHORITY_IMPERSONATION", "ALLEG": "FALSE_ALLEGATION", "THREAT": "THREAT_INTIMIDATION",
    "ISOL": "ISOLATION", "URG": "URGENCY", "DEMAND": "FINANCIAL_DEMAND", "CRED": "CREDENTIAL_REQUEST",
}
STAGE_CANONICAL = {"AUTH": "AUTHORITY", "ALLEG": "ALLEGATION", "THREAT": "THREAT", "ISOL": "ISOLATION",
                   "URG": "URGENCY", "DEMAND": "DEMAND"}

NAMES = ["Rajesh Sharma", "Anil Verma", "Sunita Rao", "Vikram Singh", "Meera Nair", "Imran Khan",
         "Prakash Joshi", "Deepak Mehta", "Kavita Iyer", "Sanjay Patil"]
BANKS = ["SBI", "HDFC Bank", "ICICI Bank", "PNB"]
UPI_HANDLES = ["okhdfcbank", "oksbi", "okaxis", "ybl", "paytm", "okicici"]
UPI_WORDS = ["verify", "refund", "support", "secure", "clearance", "kyc", "helpdesk", "claims"]
DOMAIN_WORDS = ["kyc-update", "secure-verify", "bill-clear", "duty-pay", "account-check", "quick-refund"]
AMOUNTS = [2500, 5000, 9800, 15000, 25000, 49000, 50000, 75000]
CALL_STAGE_MERGE_PROB = 0.25
PARTIAL_CALL_PROB = 0.25

# ---------------------------------------------------------------------------------------------
# Phrase pools: template -> language -> stage -> phrasings. Slots in {braces}.
# ---------------------------------------------------------------------------------------------

POOLS: dict[str, dict[str, dict[str, list[str]]]] = {
    "T1": {
        "en": {
            "AUTH": ["Hello, this is Officer {name} from the Central Bureau of Investigation. My badge number is {badge}.",
                     "I am calling from the CBI head office. I am Inspector {name}.",
                     "Good afternoon. I am Senior Officer {name} of the CBI cyber division speaking to you."],
            "ALLEG": ["Your Aadhaar number has been linked to a money laundering case involving illegal transactions.",
                      "A parcel booked using your mobile number was found with drugs and fake passports.",
                      "Your SIM card was used in a serious fraud and an FIR has been registered against you."],
            "THREAT": ["If you do not cooperate, you will be arrested today and an arrest warrant will be issued.",
                       "A non-bailable warrant is ready, and our team will arrive at your home.",
                       "You will face criminal charges and your accounts will be frozen."],
            "ISOL": ["This is a confidential investigation. Do not tell anyone, not even your family or lawyer.",
                     "You are under digital arrest. Stay on the video call and do not disconnect.",
                     "Do not contact anybody about this matter, it concerns national security."],
            "URG": ["You must act within {minutes} minutes.",
                    "This is your final notice, you need to do this immediately.",
                    "There is no time, we need this done right now."],
            "DEMAND": ["To verify your accounts, transfer {amount} rupees as a refundable deposit to {upi}.",
                       "Pay the clearance fee of Rs {amount} to the UPI ID {upi} for verification.",
                       "Send {amount} rupees to {upi}. The amount will be returned after the investigation."],
        },
        "hi-Latn": {
            "AUTH": ["Main CBI ka officer {name} bol raha hoon, mera badge number {badge} hai.",
                     "Namaste, main CBI headquarters se Inspector {name} bol raha hoon."],
            "ALLEG": ["Aapke aadhaar par money laundering ka case darj hai.",
                      "Aapke naam se ek parcel pakda gaya jisme drugs mile hain."],
            "THREAT": ["Agar aap sahyog nahi karenge to aapko giraftaar kar liya jayega.",
                       "Aapke khilaf arrest warrant jaari ho chuka hai."],
            "ISOL": ["Yeh confidential case hai, kisi ko mat batana, family ko bhi nahi.",
                     "Aap video call par bane rahiye, call cut mat kijiye."],
            "URG": ["Aapko {minutes} minute ke andar yeh karna hoga.",
                    "Turant abhi karo, der mat karo."],
            "DEMAND": ["Verification ke liye {amount} rupaye {upi} par transfer kijiye.",
                       "{upi} par {amount} rupaye jama karo, jaanch ke baad wapas milenge."],
        },
    },
    "T2": {
        "en": {
            "AUTH": ["This is {name} from FedEx customs clearance, I am connecting you to the Mumbai Customs Department.",
                     "Mumbai Customs Department speaking. I am Inspector {name}.",
                     "I am calling on behalf of the Narcotics Control Bureau, my name is {name}."],
            "ALLEG": ["A courier in your name, number {case}, was intercepted with narcotics and counterfeit currency.",
                      "Your passport and Aadhaar were used to ship illegal items abroad.",
                      "We found fake passports in a package registered to you."],
            "THREAT": ["You will be prosecuted under the narcotics act and may face imprisonment.",
                       "Legal action will be initiated and you will be taken into custody.",
                       "An arrest warrant is being prepared against you."],
            "ISOL": ["Please do not speak to anyone about this case, the investigation is strictly confidential.",
                     "Stay on the line and do not hang up until I allow you.",
                     "Do not inform your bank or relatives, it will obstruct justice."],
            "DEMAND": ["Deposit the security amount of {amount} rupees to account number {acct}, IFSC {ifsc}, held by our department.",
                       "You need to transfer {amount} rupees to the government account {acct} for case clearance.",
                       "Pay {amount} rupees by NEFT to account {acct}."],
            "URG": ["This must be completed within {minutes} minutes.",
                    "Do it immediately, otherwise the warrant will be executed.",
                    "You have only {minutes} minutes left."],
        },
        "hi-Latn": {
            "AUTH": ["Main FedEx customs se {name} bol raha hoon, aapki call Mumbai Customs ko transfer kar raha hoon.",
                     "Main Narcotics Control Bureau ka officer {name} bol raha hoon."],
            "ALLEG": ["Aapke naam par ek parcel pakda gaya hai jisme drugs aur nakli passport mile hain.",
                      "Aapke aadhaar se illegal parcel bheja gaya hai, case darj hua hai."],
            "THREAT": ["Aapko giraftaar kiya ja sakta hai, warrant nikal chuka hai.",
                       "Aap par kanooni karyavahi hogi aur jail ho sakti hai."],
            "ISOL": ["Yeh case gopniya hai, kisi ko mat batana, bank ko bhi nahi.",
                     "Call par bane rahiye aur kisi se baat mat kijiye."],
            "DEMAND": ["Security ke taur par {amount} rupaye account number {acct} mein jama karo.",
                       "Case clear karne ke liye {amount} rupaye is account mein transfer kijiye, account {acct}."],
            "URG": ["{minutes} minute ke andar yeh kar do.", "Abhi turant yeh karna hoga."],
        },
        "hi": {
            "AUTH": ["मैं नार्कोटिक्स कंट्रोल ब्यूरो का अधिकारी बोल रहा हूँ।"],
            "ALLEG": ["आपके नाम पर एक पार्सल में ड्रग्स मिले हैं और केस दर्ज हुआ है।"],
            "THREAT": ["आपको गिरफ्तार किया जा सकता है, वारंट जारी हो गया है।"],
            "ISOL": ["यह गोपनीय मामला है, किसी को मत बताना।"],
            "DEMAND": ["जांच के लिए {amount} रुपये खाता {acct} में ट्रांसफर करो।"],
            "URG": ["तुरंत यह काम करें।"],
        },
    },
    "T3": {
        "en": {
            "AUTH": ["Hello, I am {name}, a TRAI representative. Your call is being forwarded to the Cyber Police.",
                     "This is the Delhi Police cyber cell. Inspector {name} here.",
                     "I am the nodal officer {name} at the Department of Telecommunications."],
            "ALLEG": ["Your mobile number has been involved in sending obscene messages and harassing people.",
                      "Illegal advertisements were posted using your SIM, and a complaint has been lodged against you.",
                      "Your number is linked to a terror funding case under investigation."],
            "THREAT": ["Your number will be disconnected permanently and you will be sent to jail.",
                       "Police will reach your address tonight to detain you.",
                       "Strict legal action will be taken."],
            "ISOL": ["Please remain on the call and do not hang up, and do not discuss this with colleagues or friends.",
                     "You are under surveillance, do not leave the camera.",
                     "This matter is secret, do not tell your parents."],
            "URG": ["You have only {minutes} minutes to respond.",
                    "This is the last warning, deadline is tonight.",
                    "Please comply without delay."],
            "DEMAND": ["Send {amount} rupees to our verification UPI {upi}, it will be refunded.",
                       "You must pay a security deposit of {amount} to {upi}.",
                       "Transfer the bail amount of Rs {amount} to {upi}."],
        },
        "mr": {
            "AUTH": ["मी सायबर पोलीस अधिकारी बोलतोय."],
            "ALLEG": ["तुमच्या नावावर गुन्हा दाखल आहे आणि तुमच्या मोबाईलवरून बेकायदेशीर कृत्य झाले आहे."],
            "THREAT": ["तुम्हाला अटक होईल, वॉरंट निघाले आहे."],
            "ISOL": ["हे गुप्त प्रकरण आहे, कोणाला सांगू नका."],
            "URG": ["ताबडतोब हे करा."],
            "DEMAND": ["तपासासाठी {amount} रुपये {upi} वर पैसे पाठवा."],
        },
    },
    "T4": {
        "en": {
            "AUTH": ["Dear customer, this is the {bank} customer care team.",
                     "From {bank} Security Team: important notice for your account.",
                     "Alert from {bank} Fraud Department."],
            "ALLEG": ["Your KYC has expired and your account details are incomplete.",
                      "Your PAN is not updated and KYC verification is pending.",
                      "We detected suspicious activity on your account."],
            "THREAT": ["Your account will be blocked permanently.",
                       "Your debit card will be deactivated and your account frozen.",
                       "Your account will be suspended within the day."],
            "URG": ["Update immediately to avoid this.",
                    "Act within {minutes} minutes.",
                    "Please complete this today itself, this is your final notice."],
            "CRED": ["Click {url} and enter your card details and net banking login.",
                     "Share the OTP you receive to confirm.",
                     "Provide your card number and CVV to verify."],
        },
    },
    "T5": {
        "en": {
            "AUTH": ["This is the State Electricity Board billing department.",
                     "I am {name} from the Electricity Board helpdesk.",
                     "Dear consumer, this is {name} calling from the Electricity Board."],
            "ALLEG": ["Your electricity bill is unpaid for last month.",
                      "Your previous bill payment has failed and dues are pending.",
                      "Unpaid dues of Rs {amount} were found on your connection."],
            "THREAT": ["Your power connection will be disconnected tonight.",
                       "Your meter will be cut off and a penalty applied.",
                       "Connection will be terminated by 9 PM."],
            "URG": ["Pay immediately.", "Last chance, deadline is 9:30 tonight.", "Pay within {minutes} minutes."],
            "DEMAND": ["Pay Rs {amount} now using {url}.",
                       "Click {url} to pay the pending amount.",
                       "Use the payment link {url} to clear the dues."],
        },
    },
    "T6": {
        "en": {
            "AUTH": ["Hello, I am {name} calling from the DHL delivery department.",
                     "This is Blue Dart customer support, I am {name}.",
                     "I am an agent at the India Post international parcel desk."],
            "ALLEG": ["Your parcel is held at customs because the address is incomplete.",
                      "A package registered to you was seized with prohibited items.",
                      "Customs duty is pending on your international shipment."],
            "URG": ["Pay within {minutes} minutes or the parcel will be returned.",
                    "This needs to be done today itself.",
                    "Please act immediately."],
            "DEMAND": ["Pay the customs duty of Rs {amount} to {upi}.",
                       "Transfer {amount} rupees as clearance charges to {upi}.",
                       "Send Rs {amount} via UPI to {upi} to release the parcel."],
            "CRED": ["Also give me your card number and CVV for the redelivery fee.",
                     "Please share the OTP you receive to release the parcel.",
                     "Tell me your UPI PIN to confirm the refund."],
        },
        "hi-Latn": {
            "AUTH": ["Main DHL delivery department se {name} bol raha hoon.",
                     "Main Blue Dart customer support se {name} bol raha hoon."],
            "ALLEG": ["Aapka parcel customs mein ruka hua hai, customs duty pending hai.",
                      "Aapke parcel mein illegal saman mila hai."],
            "URG": ["Abhi turant payment karo.", "{minutes} minute ke andar karna hoga."],
            "DEMAND": ["{upi} par {amount} rupaye bhejo.",
                       "Customs duty ke liye {amount} rupaye {upi} par transfer kijiye."],
            "CRED": ["Apna card number aur CVV bataiye.", "OTP batao jo aapko aaya hai."],
        },
    },
}

TEMPLATES = {
    "T1": dict(scenario_type="digital_arrest_cbi", channel="call", institution="CENTRAL_AGENCY", payment="UPI",
               stages=["AUTH", "ALLEG", "THREAT", "ISOL", "URG", "DEMAND"], ids=["phone", "upi"]),
    "T2": dict(scenario_type="digital_arrest_courier_customs", channel="call", institution="COURIER_CUSTOMS",
               payment="BANK_TRANSFER", stages=["AUTH", "ALLEG", "THREAT", "ISOL", "DEMAND", "URG"],
               ids=["phone", "acct"]),
    "T3": dict(scenario_type="digital_arrest_telecom_police", channel="call", institution="TELECOM", payment="UPI",
               stages=["AUTH", "ALLEG", "THREAT", "ISOL", "URG", "DEMAND"], ids=["phone", "upi"]),
    "T4": dict(scenario_type="bank_kyc_phishing", channel="sms", institution="BANK", payment="LINK_PAYMENT",
               stages=["AUTH", "ALLEG", "THREAT", "URG", "CRED"], ids=["domain"], path="kyc"),
    "T5": dict(scenario_type="payment_link_bill", channel="sms", institution="GOVT_OTHER", payment="LINK_PAYMENT",
               stages=["AUTH", "ALLEG", "THREAT", "URG", "DEMAND"], ids=["domain"], path="pay"),
    "T6": dict(scenario_type="courier_customs_parcel", channel="call", institution="COURIER_CUSTOMS", payment="UPI",
               stages=["AUTH", "ALLEG", "URG", "DEMAND", "CRED"], ids=["phone", "upi"]),
}

VICTIM = {
    "en": ["Okay, what should I do?", "Sir, I did not do anything.", "Please, I will cooperate.",
           "I understand, tell me.", "Yes, I am listening."],
    "hi-Latn": ["Ji boliye, main sun raha hoon.", "Sir maine kuch galat nahi kiya.", "Theek hai, bataiye kya karna hai."],
    "hi": ["जी बोलिए।", "ठीक है, बताइए।"],
    "mr": ["ठीक आहे, सांगा.", "हो, मी ऐकतोय."],
}
CALLBACK = {"en": "If we get disconnected, call me back on {phone}.",
            "hi-Latn": "Agar call kat jaye to {phone} par call karna."}

NEG_POOLS = {
    "N1": dict(channel="sms", speakers=("sender",), labels=["LEGITIMATE"], phrases=[
        "Dear customer, Rs {amount} was debited from your account. If this was not done by you, call our official helpline 1930.",
        "Your account has been credited with Rs {amount}. Thank you for banking with us.",
        "Rs {amount} was spent on your card at a merchant. For queries, visit your nearest branch."]),
    "N2": dict(channel="sms", speakers=("sender",), labels=["LEGITIMATE"], phrases=[
        "Your one time password for login has been sent to your registered mobile. Never share it with anyone.",
        "Do not share your OTP with anyone, our staff will never ask for it.",
        "Your verification code is valid for 10 minutes. Never share it with anyone."]),
    "N3": dict(channel="sms", speakers=("sender",), labels=["LEGITIMATE"], phrases=[
        "Your order has been dispatched and will be delivered tomorrow. Track it in the official app.",
        "Your parcel is out for delivery today. Please keep your ID ready.",
        "Your package has been delivered. Thank you for shopping with us."]),
    "N4": dict(channel="sms", speakers=("sender",), labels=["LEGITIMATE"], phrases=[
        "Your new debit card is ready. Please visit your nearest branch with a photo ID to collect it.",
        "Your statement has been generated. For help, call the official customer care number.",
        "Your cheque book has been dispatched. If you have not received it in a week, visit your branch."]),
    "N5": dict(channel="call", speakers=("caller", "victim"), labels=["AUTHORITY_IMPERSONATION", "LEGITIMATE"], phrases=[
        "Hello, this is {name} from the local police station. Your passport verification is scheduled for tomorrow. "
        "Please visit the station with your original documents. No payment is required.",
        "This is the police station calling regarding your address verification. Kindly visit the station with your ID. "
        "There is no fee."]),
    "N6": dict(channel="call", speakers=("caller", "victim"), labels=[], phrases=[
        "Hi beta, are you coming home for dinner?",
        "Call me when you reach, I will keep the food ready.",
        "Your uncle is visiting this weekend, please plan accordingly."]),
}


# ---------------------------------------------------------------------------------------------
# Synthetic identifiers
# ---------------------------------------------------------------------------------------------

def fresh_id(rng: random.Random, kind: str) -> str:
    if kind == "phone":
        return f"+91 98765 {rng.randint(10000, 99999)}"
    if kind == "upi":
        return f"{rng.choice(UPI_WORDS)}{rng.randint(10, 99)}@{rng.choice(UPI_HANDLES)}"
    if kind == "domain":
        return f"{rng.choice(DOMAIN_WORDS)}-{rng.randint(100, 999)}.example"
    if kind == "acct":
        return str(rng.randint(5, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(11))   # 12 digits
    raise ValueError(kind)


def canonical_phone(display: str) -> str:
    return "+" + re.sub(r"\D", "", display)


def slots_for(rng: random.Random, ids: dict, path: str | None) -> dict:
    domain = ids.get("domain", "")
    return {
        "name": rng.choice(NAMES), "badge": str(rng.randint(10000, 99999)), "bank": rng.choice(BANKS),
        "amount": rng.choice(AMOUNTS), "minutes": rng.choice([10, 15, 20, 30, 45]),
        "case": f"NCB-{rng.randint(1000, 9999)}", "ifsc": f"HDFC000{rng.randint(1000, 9999)}",
        "phone": ids.get("phone", ""), "upi": ids.get("upi", ""), "acct": ids.get("acct", ""),
        "domain": domain, "url": f"https://{domain}/{path}" if domain else "",
    }


# ---------------------------------------------------------------------------------------------
# Incident builders
# ---------------------------------------------------------------------------------------------

def build_campaign_incident(rng, tid, tpl, lang, ids, partial_ok=True):
    pools = POOLS[tid][lang]
    stages = list(tpl["stages"])
    if tpl["channel"] == "call" and partial_ok and rng.random() < PARTIAL_CALL_PROB and len(stages) > 3:
        stages = stages[:rng.randint(2, len(stages) - 1)]       # a call that is cut off
    slots = slots_for(rng, ids, tpl.get("path"))

    # Group stages into turns; on calls adjacent stages are sometimes spoken in one turn
    groups: list[list[str]] = []
    for stage in stages:
        if (tpl["channel"] == "call" and groups and len(groups[-1]) == 1
                and rng.random() < CALL_STAGE_MERGE_PROB):
            groups[-1].append(stage)
        else:
            groups.append([stage])

    utterances = []
    t = 0.0
    for gi, group in enumerate(groups):
        text = " ".join(rng.choice(pools[s]).format(**slots) for s in group)
        if gi == 0 and tpl["channel"] == "call" and lang in CALLBACK and ids.get("phone"):
            text += " " + CALLBACK[lang].format(**slots)
        labels = sorted({STAGE_LABEL[s] for s in group}, key=TACTIC_LABELS.index)
        speaker = "caller" if tpl["channel"] == "call" else "sender"
        utterances.append({"speaker": speaker, "text": text, "tactic_labels": labels,
                           "t_start_sec": round(t, 1) if tpl["channel"] == "call" else None})
        t += rng.uniform(8, 25)
        if tpl["channel"] == "call" and gi < len(groups) - 1:
            utterances.append({"speaker": "victim", "text": rng.choice(VICTIM[lang]), "tactic_labels": [],
                               "t_start_sec": round(t, 1)})
            t += rng.uniform(4, 12)
    sequence = [STAGE_CANONICAL[s] for s in stages if s in STAGE_CANONICAL]
    return utterances, sequence, "CRED" in stages


def build_negative_incident(rng, nid, ids_unused=None):
    cfg = NEG_POOLS[nid]
    slots = {"amount": rng.choice(AMOUNTS), "name": rng.choice(NAMES)}
    n_messages = rng.choice([1, 2]) if cfg["channel"] == "sms" else 1
    phrases = rng.sample(cfg["phrases"], k=min(n_messages, len(cfg["phrases"])))
    utterances, t = [], 0.0
    for p in phrases:
        utterances.append({"speaker": cfg["speakers"][0], "text": p.format(**slots),
                           "tactic_labels": sorted(cfg["labels"], key=TACTIC_LABELS.index),
                           "t_start_sec": round(t, 1) if cfg["channel"] == "call" else None})
        t += rng.uniform(8, 25)
    if cfg["channel"] == "call":
        utterances.append({"speaker": "victim", "text": rng.choice(VICTIM["en"]), "tactic_labels": [],
                           "t_start_sec": round(t, 1)})
    return utterances, cfg["channel"]


def mentions_in(text_all: str, ids: dict) -> list[dict]:
    out = []
    if ids.get("phone") and ids["phone"] in text_all:
        out.append({"type": "PHONE", "canonical": canonical_phone(ids["phone"])})
    if ids.get("upi") and ids["upi"] in text_all:
        out.append({"type": "UPI_HANDLE", "canonical": ids["upi"].lower()})
    if ids.get("domain") and ids["domain"] in text_all:
        out.append({"type": "DOMAIN", "canonical": ids["domain"]})
    return out


def generate(seed: int, rotation: float, variants: int = 12) -> list[dict]:
    rng = random.Random(seed)
    base_date = date(2026, 8, 1)
    records: list[dict] = []
    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        return f"inc_{counter:04d}"

    for tid, tpl in TEMPLATES.items():
        langs = [lang for lang in POOLS[tid] if lang in ("en", "hi-Latn")]
        for inst in range(variants // 3):
            instance_id = f"{tid}-c{inst + 1}"
            ids = {k: fresh_id(rng, k) for k in tpl["ids"]}
            day0 = base_date + timedelta(days=rng.randint(0, 40))
            for k in range(3):
                variant_index = inst * 3 + k
                rotated: list[str] = []
                if k > 0:
                    for field in tpl["ids"]:
                        if rng.random() < rotation:
                            ids[field] = fresh_id(rng, field)
                            rotated.append(field)
                # a handful of Devanagari Hindi (T2) and Marathi (T3) incidents; the rest English / Hinglish
                if tid == "T2" and variant_index >= variants - 2:
                    lang = "hi"
                elif tid == "T3" and variant_index >= variants - 2:
                    lang = "mr"
                else:
                    lang = "hi-Latn" if (len(langs) > 1 and rng.random() < 0.4) else "en"
                utterances, sequence, cred = build_campaign_incident(rng, tid, tpl, lang, dict(ids),
                                                                     partial_ok=lang in ("en", "hi-Latn"))
                incident_id = next_id()
                all_text = " ".join(u["text"] for u in utterances)
                records.append({
                    "incident_id": incident_id, "conversation_id": f"conv_{incident_id[4:]}",
                    "scenario_type": tpl["scenario_type"], "campaign_template_id": tid,
                    "campaign_instance_id": instance_id, "decoy_type": None,
                    "source_channel": tpl["channel"], "language": lang,
                    "timestamp": (day0 + timedelta(days=rng.randint(0, 20) * k)).isoformat(),
                    "rotated_fields": rotated, "identifiers": dict(ids),
                    "entity_mentions": mentions_in(all_text, ids),
                    "expected_stage_sequence": sequence, "credential_requested": cred,
                    "institution_class": tpl["institution"], "payment_channel": tpl["payment"],
                    "utterances": utterances, "expected_associations": [],
                    "is_synthetic": True, "provenance": "generator", "generator_version": GENERATOR_VERSION,
                    "seed": seed, "rotation": rotation, "split": TEMPLATE_SPLIT[tid],
                })

    for nid, count in NEGATIVE_COUNTS.items():
        for _ in range(count):
            utterances, channel = build_negative_incident(rng, nid)
            incident_id = next_id()
            records.append({
                "incident_id": incident_id, "conversation_id": f"conv_{incident_id[4:]}",
                "scenario_type": "legitimate", "campaign_template_id": nid, "campaign_instance_id": None,
                "decoy_type": None, "source_channel": channel, "language": "en",
                "timestamp": (base_date + timedelta(days=rng.randint(0, 80))).isoformat(),
                "rotated_fields": [], "identifiers": {}, "entity_mentions": [],
                "expected_stage_sequence": (["AUTHORITY"] if nid == "N5" else []), "credential_requested": False,
                "institution_class": "POLICE" if nid == "N5" else ("BANK" if nid in ("N1", "N2", "N4") else "UNKNOWN"),
                "payment_channel": "NONE", "utterances": utterances, "expected_associations": [],
                "is_synthetic": True, "provenance": "generator", "generator_version": GENERATOR_VERSION,
                "seed": seed, "rotation": rotation, "split": NEGATIVE_SPLIT[nid],
            })

    # Ground truth: two incidents are a true pair iff they share a campaign_instance_id
    by_instance: dict[str, list[str]] = {}
    for r in records:
        if r["campaign_instance_id"]:
            by_instance.setdefault(r["campaign_instance_id"], []).append(r["incident_id"])
    for r in records:
        if r["campaign_instance_id"]:
            r["expected_associations"] = [i for i in by_instance[r["campaign_instance_id"]] if i != r["incident_id"]]

    # utterance ids and indexes
    for r in records:
        for i, u in enumerate(r["utterances"]):
            u["idx"] = i
            u["utterance_id"] = f"{r['incident_id']}_u{i}"
    return records


# ---------------------------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------------------------

REQUIRED = ["incident_id", "conversation_id", "scenario_type", "campaign_template_id", "campaign_instance_id",
            "source_channel", "language", "timestamp", "rotated_fields", "identifiers", "entity_mentions",
            "expected_stage_sequence", "institution_class", "payment_channel", "utterances",
            "expected_associations", "is_synthetic", "provenance", "generator_version", "seed", "split"]
LANGS = {"en", "hi", "hi-Latn", "mr", "mixed"}
SPLITS = {"train", "dev", "test", "heldout"}
PHONE_RE = re.compile(r"^\+91 98765 \d{5}$")
UPI_RE = re.compile(r"^[a-z]+\d{2}@(?:%s)$" % "|".join(UPI_HANDLES))
DOMAIN_RE = re.compile(r"^[a-z\-]+-\d{3}\.example$")


def validate(records: list[dict]) -> list[str]:
    errors: list[str] = []
    seen = set()
    for r in records:
        iid = r.get("incident_id", "?")
        missing = [k for k in REQUIRED if k not in r]
        if missing:
            errors.append(f"{iid}: missing fields {missing}")
            continue
        if iid in seen:
            errors.append(f"{iid}: duplicate incident_id")
        seen.add(iid)
        if r["is_synthetic"] is not True:
            errors.append(f"{iid}: is_synthetic must be true")
        if r["language"] not in LANGS:
            errors.append(f"{iid}: bad language {r['language']!r}")
        if r["split"] not in SPLITS:
            errors.append(f"{iid}: bad split {r['split']!r}")
        tid = r["campaign_template_id"]
        if r["split"] != {**TEMPLATE_SPLIT, **NEGATIVE_SPLIT}.get(tid):
            errors.append(f"{iid}: split {r['split']} does not match template {tid} (splits are by template)")
        if (r["scenario_type"] == "legitimate") != (r["campaign_instance_id"] is None):
            errors.append(f"{iid}: campaign_instance_id must be null exactly for non-campaign incidents")
        for s in r["expected_stage_sequence"]:
            if s not in CANONICAL_STAGES:
                errors.append(f"{iid}: bad stage {s!r}")
        ids = r["identifiers"]
        if "phone" in ids and not PHONE_RE.match(ids["phone"]):
            errors.append(f"{iid}: phone {ids['phone']!r} is not in the synthetic example range")
        if "upi" in ids and not UPI_RE.match(ids["upi"]):
            errors.append(f"{iid}: upi {ids['upi']!r} is not a synthetic handle")
        if "domain" in ids and not DOMAIN_RE.match(ids["domain"]):
            errors.append(f"{iid}: domain {ids['domain']!r} is not a reserved .example domain")
        if not r["utterances"]:
            errors.append(f"{iid}: no utterances")
        for i, u in enumerate(r["utterances"]):
            if u.get("idx") != i:
                errors.append(f"{iid}: utterance idx not contiguous at {i}")
            bad = [lab for lab in u["tactic_labels"] if lab not in TACTIC_LABELS]
            if bad:
                errors.append(f"{iid}: unknown labels {bad}")
            if not u["text"].strip():
                errors.append(f"{iid}: empty utterance {i}")
            # No real-looking secret may be present: the redactor must find nothing to remove
            if redact_text(u["text"]).text != u["text"]:
                errors.append(f"{iid}: utterance {i} contains a redactable secret-like value")
    return errors


def write(records: list[dict], out: Path) -> int:
    lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in records]
    data = ("\n".join(lines) + "\n").encode("utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return len(data)


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the synthetic VIGIL dataset (JSONL).")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--rotation", type=float, default=0.5, help="identifier rotation probability 0.0-1.0")
    ap.add_argument("--variants", type=int, default=12, help="incidents per campaign template (multiple of 3)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    if args.validate_only:
        records = load(args.out)
    else:
        if not 0.0 <= args.rotation <= 1.0 or args.variants % 3:
            ap.error("--rotation must be within 0..1 and --variants a multiple of 3")
        records = generate(args.seed, args.rotation, args.variants)

    errors = validate(records)
    if errors:
        print(f"VALIDATION FAILED ({len(errors)} problems):")
        for e in errors[:20]:
            print("  -", e)
        return 1
    if not args.validate_only:
        size = write(records, args.out)
        if size > MAX_BYTES:
            print(f"Output is {size} bytes, over the {MAX_BYTES} byte budget")
            return 1
        print(f"Wrote {args.out} ({size} bytes)")
    n_utt = sum(len(r["utterances"]) for r in records)
    splits = {s: sum(1 for r in records if r["split"] == s) for s in ("train", "dev", "test")}
    print(f"OK: {len(records)} incidents, {n_utt} utterances, splits {splits}, all validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
