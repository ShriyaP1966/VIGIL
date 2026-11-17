"""Rule-based tactic extractor: lexicon integrity, per-label behaviour, spans, persistence."""
import json
import re
import sys
from pathlib import Path

import pytest

from ai_engine.extraction.interface import UtteranceInput
from ai_engine.extraction.rule_extractor import DEFAULT_LEXICON, RuleExtractor, get_default_extractor
from ai_engine.extraction.tactics import TACTIC_LABELS
from ai_engine.extraction.turns import parse_labelled_turns
from backend.app.models.models import Analysis, TacticEvent, Utterance
from backend.app.schemas.schemas import EvidenceCreate, IncidentCreate
from backend.app.services.incident_service import create_incident, run_incident_analysis

ROOT = Path(__file__).resolve().parents[2]


def labels_of(text: str, speaker: str = "caller") -> set[str]:
    res = get_default_extractor().analyze([UtteranceInput(idx=0, speaker=speaker, text=text)])
    return set(res.utterances[0].tactic_labels)


# ---------------------------------------------------------------------------------------
# Lexicon integrity
# ---------------------------------------------------------------------------------------

def test_lexicon_json_matches_its_builder():
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_lexicon
    assert DEFAULT_LEXICON.read_text(encoding="utf-8") == build_lexicon.render(), \
        "data/lexicon.json is stale: run python scripts/build_lexicon.py"


def test_every_pattern_compiles_and_ids_are_unique():
    lex = json.loads(DEFAULT_LEXICON.read_text(encoding="utf-8"))
    assert set(lex["labels"]) == set(TACTIC_LABELS)
    ids = [r["id"] for rules in lex["labels"].values() for r in rules]
    assert len(ids) == len(set(ids))
    RuleExtractor()  # compiles everything (raises on a bad pattern)
    for rules in lex["labels"].values():
        assert all(0.5 <= r["confidence"] <= 1.0 for r in rules)


def test_extractor_is_deterministic_and_offline():
    text = "Main CBI officer bol raha hoon. Aapke naam par case hai. Turant paise bhejo."
    a = get_default_extractor().analyze([UtteranceInput(idx=0, speaker="caller", text=text)])
    b = RuleExtractor().analyze([UtteranceInput(idx=0, speaker="caller", text=text)])
    assert a.model_dump() == b.model_dump()
    assert a.extractor_name == "rules" and a.fallback_used is False


# ---------------------------------------------------------------------------------------
# Hand-written positives (English, Hinglish, Devanagari Hindi, Marathi)
# ---------------------------------------------------------------------------------------

POSITIVES = [
    ("AUTHORITY_IMPERSONATION", "I am Inspector Rao calling from the Cyber Crime Cell."),
    ("AUTHORITY_IMPERSONATION", "This is Mumbai Customs Department."),
    ("AUTHORITY_IMPERSONATION", "Main CBI officer Rajesh Sharma bol raha hoon."),
    ("AUTHORITY_IMPERSONATION", "मैं सीबीआई अधिकारी बोल रहा हूँ।"),
    ("AUTHORITY_IMPERSONATION", "मी सायबर पोलीस अधिकारी बोलतोय."),
    ("FALSE_ALLEGATION", "Your Aadhaar is linked to a money laundering case."),
    ("FALSE_ALLEGATION", "A parcel in your name contains drugs found by customs."),
    ("FALSE_ALLEGATION", "Aapke naam par illegal parcel pakda gaya hai, fraud case hai."),
    ("FALSE_ALLEGATION", "आपके नाम पर केस दर्ज है"),
    ("FALSE_ALLEGATION", "तुमच्या नावावर गुन्हा दाखल आहे"),
    ("FALSE_ALLEGATION", "Your KYC is pending and your account is suspicious."),
    ("THREAT_INTIMIDATION", "You will be arrested if you do not cooperate."),
    ("THREAT_INTIMIDATION", "An arrest warrant has been issued against you."),
    ("THREAT_INTIMIDATION", "Your SIM will be blocked permanently."),
    ("THREAT_INTIMIDATION", "Aap giraftaar ho jayenge."),
    ("THREAT_INTIMIDATION", "आप गिरफ्तार होंगे"),
    ("ISOLATION", "Do not tell anyone about this call, not even your family."),
    ("ISOLATION", "Stay on the video call and do not disconnect."),
    ("ISOLATION", "Kisi ko mat batana."),
    ("ISOLATION", "किसी को मत बताना"),
    ("ISOLATION", "कोणाला सांगू नका"),
    ("URGENCY", "Pay within 30 minutes."),
    ("URGENCY", "You must do it immediately."),
    ("URGENCY", "Turant karo, der mat karna."),
    ("URGENCY", "तुरंत करें"),
    ("URGENCY", "ताबडतोब करा"),
    ("FINANCIAL_DEMAND", "Transfer the security deposit to our account."),
    ("FINANCIAL_DEMAND", "Pay Rs 50000 as clearance charges."),
    ("FINANCIAL_DEMAND", "Send the money to verify-cbi@okhdfcbank."),
    ("FINANCIAL_DEMAND", "Buy gift cards and send the codes."),
    ("FINANCIAL_DEMAND", "Paise bhejo abhi."),
    ("FINANCIAL_DEMAND", "पैसे भेजो"),
    ("FINANCIAL_DEMAND", "पैसे पाठवा"),
    ("CREDENTIAL_REQUEST", "Please share the OTP you received."),
    ("CREDENTIAL_REQUEST", "Tell me your UPI PIN."),
    ("CREDENTIAL_REQUEST", "OTP batao."),
    ("CREDENTIAL_REQUEST", "ओटीपी बताओ"),
    ("LEGITIMATE", "Never share your OTP with anyone."),
    ("LEGITIMATE", "Please visit your nearest branch with photo ID."),
    ("LEGITIMATE", "For help call the official helpline 1930."),
    ("LEGITIMATE", "No payment is required."),
    ("LEGITIMATE", "Your order has been dispatched."),
    ("OTHER_SUSPICIOUS", "You have won a lottery, claim the prize money."),
]


@pytest.mark.parametrize("label,text", POSITIVES)
def test_label_fires(label, text):
    assert label in labels_of(text)


# Text that must NOT produce the named label
NEGATIVES = [
    ("CREDENTIAL_REQUEST", "Never share your OTP with anyone."),
    ("CREDENTIAL_REQUEST", "Please do not share your PIN or password."),
    ("CREDENTIAL_REQUEST", "OTP kisi ko share na karein."),
    ("ISOLATION", "Never share your OTP or password with anyone."),
    ("AUTHORITY_IMPERSONATION", "Hi beta, are you coming home for dinner?"),
    ("FINANCIAL_DEMAND", "Your order has been dispatched and will arrive tomorrow."),
    ("FINANCIAL_DEMAND", "Rs 5000 credited to your account."),
    ("THREAT_INTIMIDATION", "Please confirm your first appointment."),
    ("URGENCY", "Your parcel arrives within 2 hours."),
    ("FALSE_ALLEGATION", "Dear customer, your monthly statement has been dispatched."),
]


@pytest.mark.parametrize("label,text", NEGATIVES)
def test_label_does_not_fire(label, text):
    assert label not in labels_of(text)


def test_plain_chat_gets_no_labels():
    assert labels_of("Hi beta, are you coming home for dinner? Call me when you reach.") == set()


def test_victim_turns_are_never_scored():
    assert labels_of("Arrest? I will be arrested? Pay money? OTP?", speaker="victim") == set()
    assert labels_of("Arrest? I will be arrested?", speaker="Customer") == set()


def test_multi_label_utterance_and_confidences():
    res = get_default_extractor().analyze([UtteranceInput(
        idx=0, speaker="caller",
        text="Transfer the deposit to verify-cbi@okhdfcbank immediately or you will be arrested.")])
    u = res.utterances[0]
    assert {"FINANCIAL_DEMAND", "URGENCY", "THREAT_INTIMIDATION"} <= set(u.tactic_labels)
    assert all(0.5 <= u.confidence_scores[lab] <= 1.0 for lab in u.tactic_labels)


# ---------------------------------------------------------------------------------------
# Spans point at the original text, even when invisible characters are inserted
# ---------------------------------------------------------------------------------------

def test_spans_slice_the_original_text():
    text = "Hello. You will be arrested within 30 minutes. Bye."
    u = get_default_extractor().analyze([UtteranceInput(idx=0, speaker="caller", text=text)]).utterances[0]
    for label in u.tactic_labels:
        assert u.label_spans[label]
        for s, e in u.label_spans[label]:
            assert 0 <= s < e <= len(text)
    s, e = u.label_spans["THREAT_INTIMIDATION"][0]
    assert text[s:e] == "You will be arrested"


def test_zero_width_characters_do_not_evade_rules():
    text = "You will be arr​ested right away"
    u = get_default_extractor().analyze([UtteranceInput(idx=0, speaker="caller", text=text)]).utterances[0]
    assert "THREAT_INTIMIDATION" in u.tactic_labels
    s, e = u.label_spans["THREAT_INTIMIDATION"][0]
    assert text[s:e].replace("​", "") == "You will be arrested"


# ---------------------------------------------------------------------------------------
# Institution, payment channel, language
# ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("text,inst", [
    ("I am calling from the CBI about your case", "CENTRAL_AGENCY"),
    ("This is the Mumbai Police cyber crime cell", "POLICE"),
    ("FedEx parcel held at customs", "COURIER_CUSTOMS"),
    ("Your SBI KYC is pending", "BANK"),
    ("Hi beta, dinner at eight", "UNKNOWN"),
])
def test_institution_class(text, inst):
    res = get_default_extractor().analyze([UtteranceInput(idx=0, speaker="caller", text=text)])
    assert res.institution_class == inst


@pytest.mark.parametrize("text,channel", [
    ("Transfer the deposit to verify-cbi@okhdfcbank now", "UPI"),
    ("Pay the fee by NEFT to this account number", "BANK_TRANSFER"),
    ("Buy gift cards and send the codes", "GIFT_CARD"),
    ("Send money to my bitcoin wallet address", "CRYPTO"),
    ("Pay the fine using the payment link https://pay.example/x", "LINK_PAYMENT"),
    ("Your parcel was dispatched today", "NONE"),
])
def test_payment_channel(text, channel):
    res = get_default_extractor().analyze([UtteranceInput(idx=0, speaker="caller", text=text)])
    assert res.payment_channel == channel


def test_language_is_detected_or_mixed():
    en = get_default_extractor().analyze([UtteranceInput(idx=0, speaker="caller", text="This is a plain English call alert.")])
    assert en.detected_language == "en"
    mixed = get_default_extractor().analyze([
        UtteranceInput(idx=0, speaker="caller", text="This is a plain English call alert."),
        UtteranceInput(idx=1, speaker="caller", text="Aapke naam par warrant hai, turant paise bhejo."),
    ])
    assert mixed.detected_language == "mixed"


# ---------------------------------------------------------------------------------------
# Transcript turn parsing
# ---------------------------------------------------------------------------------------

def test_parse_labelled_turns():
    turns = parse_labelled_turns("Caller: This is the CBI.\nVictim: What?\nthat is all\nCaller: Pay now.")
    assert [t["speaker"] for t in turns] == ["caller", "victim", "caller"]
    assert turns[1]["text"] == "What?\nthat is all"


@pytest.mark.parametrize("text", [
    "Just a plain pasted message with no labels.",
    "Note: this has only one label line\nand more text",
    "Caller: only the caller speaks\nCaller: again",
    "intro line before any label\nCaller: hi\nVictim: hello",
])
def test_non_transcripts_are_not_split(text):
    assert parse_labelled_turns(text) is None


# ---------------------------------------------------------------------------------------
# Pipeline integration: tactic_events, fingerprint, re-analysis
# ---------------------------------------------------------------------------------------

SCAM = ("Caller: This is Inspector Rao from the Cyber Crime Cell. Your Aadhaar is linked to a money laundering case.\n"
        "Victim: Arrest? I did nothing!\n"
        "Caller: You will be arrested within 30 minutes. Do not tell anyone and stay on the video call.\n"
        "Caller: Transfer the security deposit to our account immediately.")


@pytest.fixture
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_tactic_events_are_persisted_with_spans_and_not_duplicated(db):
    inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(text=SCAM)]))
    run_incident_analysis(db, inc.id)
    first = db.query(TacticEvent).filter(TacticEvent.incident_id == inc.id).count()
    assert first > 0
    run_incident_analysis(db, inc.id)  # re-analysis replaces, never duplicates
    assert db.query(TacticEvent).filter(TacticEvent.incident_id == inc.id).count() == first

    utt = {u.id: u for u in db.query(Utterance).all()}
    for ev in db.query(TacticEvent).filter(TacticEvent.incident_id == inc.id):
        s, e = (int(x) for x in ev.evidence_span.split(":"))
        assert 0 <= s < e <= len(utt[ev.utterance_id].text)
        assert 0.5 <= ev.confidence <= 1.0
        assert utt[ev.utterance_id].speaker != "victim"   # victim turns carry no tactic events


def test_pasted_transcript_is_split_into_speaker_turns(db):
    inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(text=SCAM)]))
    speakers = [u.speaker for u in db.query(Utterance).order_by(Utterance.id)]
    assert speakers == ["caller", "victim", "caller", "caller"]
    assert inc.id


def test_fingerprint_and_analysis_record_the_rule_extractor(db):
    inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(text=SCAM)]))
    run_incident_analysis(db, inc.id)
    analysis = db.query(Analysis).filter(Analysis.incident_id == inc.id).order_by(Analysis.id.desc()).first()
    fp = json.loads(analysis.fingerprint_json)
    assert fp["stage_sequence"] == ["AUTHORITY", "ALLEGATION", "THREAT", "ISOLATION", "URGENCY", "DEMAND"]
    assert fp["institution_class"] in {"POLICE", "CENTRAL_AGENCY"}
    assert fp["channel"] == "call" and fp["credential_requested"] is False
    assert analysis.extractor == "rules" and analysis.extractor_version.startswith("rules@")
    assert analysis.fallback_used is False


def test_partial_call_gives_partial_sequence(db):
    inc = create_incident(db, IncidentCreate(title="t", evidence=[EvidenceCreate(
        text="This is Inspector Rao from the Cyber Crime Cell. Your Aadhaar is linked to a money laundering case.")]))
    run_incident_analysis(db, inc.id)
    fp = json.loads(db.query(Analysis).filter(Analysis.incident_id == inc.id).one().fingerprint_json)
    assert fp["stage_sequence"] == ["AUTHORITY", "ALLEGATION"]


def test_extractor_imports_no_network_or_llm_client():
    # The default extractor needs only the lexicon file: no HTTP client, socket, or LLM SDK is imported.
    src = (ROOT / "ai_engine/extraction/rule_extractor.py").read_text(encoding="utf-8")
    imports = "\n".join(line for line in src.splitlines() if re.match(r"\s*(import|from)\s", line))
    assert not re.search(r"requests|httpx|urllib|socket|aiohttp|genai|google|openai", imports)
