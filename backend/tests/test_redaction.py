"""Unit tests for ai_engine.privacy.redaction (blueprint §5.5)."""
import random
import re

import pytest

from ai_engine.extraction.entity_extractor import extract_entities
from ai_engine.privacy.redaction import (
    luhn_valid, redact_evidence, redact_text, redact_turns, verhoeff_valid,
)
from backend.app.services.seed_service import SEED_INCIDENTS


def make_card(rng: random.Random, prefix: str = "4", length: int = 16) -> str:
    body = prefix + "".join(str(rng.randint(0, 9)) for _ in range(length - len(prefix) - 1))
    for check in range(10):
        if luhn_valid(body + str(check)):
            return body + str(check)
    raise AssertionError("unreachable")


def make_aadhaar(rng: random.Random) -> str:
    body = str(rng.randint(2, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(10))
    for check in range(10):
        if verhoeff_valid(body + str(check)):
            return body + str(check)
    raise AssertionError("unreachable")


AADHAAR = make_aadhaar(random.Random(7))
AADHAAR_FMT = f"{AADHAAR[:4]} {AADHAAR[4:8]} {AADHAAR[8:]}"


def test_checksum_implementations_are_correct():
    assert luhn_valid("4111111111111111") and luhn_valid("378282246310005")
    assert not luhn_valid("4111111111111112")
    assert verhoeff_valid("2363")  # standard Verhoeff example (236 + check digit 3)
    assert not verhoeff_valid("2364")


# (text, expected kind, secret that must disappear)
POSITIVES = [
    ("Your OTP is 482913, do not share.", "OTP", "482913"),
    ("otp batao 4829 abhi", "OTP", "4829"),
    ("OTP: 4 8 2 9 1 3", "OTP", "4 8 2 9 1 3"),
    ("One time password is 482913", "OTP", "482913"),
    ("482913 is your OTP", "OTP", "482913"),
    ("verification code 773104 sent", "OTP", "773104"),
    ("ओटीपी ४८२९१३ है", "OTP", "४८२९१३"),                       # Devanagari digits
    ("OTP is ４８２９１３", "OTP", "４８２９１३"),                    # fullwidth digits
    ("OTP is 48​29​13", "OTP", "48​29​13"),  # zero-width characters inside
    ("Share your UPI PIN 7391 now", "PIN", "7391"),
    ("mpin hai 739155", "PIN", "739155"),
    ("CVV 829 on the back", "CVV", "829"),
    ("cvv2: 8291", "CVV", "8291"),
    ("my password is Hunter@2026x ok", "PASSWORD", "Hunter@2026x"),
    ("password: abc12345", "PASSWORD", "abc12345"),
    ("net banking pwd hai Zx9#kQ", "PASSWORD", "Zx9#kQ"),
    ("password hunter2 batao", "PASSWORD", "hunter2"),            # no separator, but contains a digit
    ("pay with 4111111111111111 today", "CARD", "4111111111111111"),
    ("card 5555-5555-5555-4444 exp 08/27", "CARD", "5555-5555-5555-4444"),
    ("debit card 1234 5678 9012 3456", "CARD", "1234 5678 9012 3456"),   # not Luhn-valid, card cue
    (f"my Aadhaar number {AADHAAR_FMT}", "AADHAAR", AADHAAR_FMT),
    (f"aadhaar {AADHAAR} is linked", "AADHAAR", AADHAAR),
    (f"id {AADHAAR_FMT} attached", "AADHAAR", AADHAAR_FMT),       # formatted + Verhoeff-valid, no cue
    ("Caller: Tell me the OTP\nVictim: 482913", "OTP", "482913"),
    ("Please share your PIN\nVictim: it is 7391", "PIN", "7391"),
    ("Caller: password batao\nVictim: Hunter@2026x", "PASSWORD", "Hunter@2026x"),
]


@pytest.mark.parametrize("text,kind,secret", POSITIVES)
def test_secrets_are_redacted(text, kind, secret):
    res = redact_text(text)
    assert secret not in res.text
    assert f"[REDACTED:{kind}]" in res.text
    assert kind in {e.kind for e in res.events}


@pytest.mark.parametrize("text,kind,secret", POSITIVES)
def test_redaction_is_idempotent_and_event_spans_point_at_placeholders(text, kind, secret):
    once = redact_text(text)
    assert redact_text(once.text).text == once.text
    for ev in once.events:
        assert once.text[ev.span_start:ev.span_end] == f"[REDACTED:{ev.kind}]"


def test_card_expiry_is_redacted_with_the_card():
    res = redact_text("card 5555-5555-5555-4444 exp 08/27 thanks")
    assert "08/27" not in res.text
    assert {e.kind for e in res.events} == {"CARD", "CARD_EXPIRY"}


def test_cue_words_survive_so_a_credential_request_is_still_visible():
    assert "share the OTP" in redact_text("please share the OTP 482913").text


# Text that must NOT change: identifiers VIGIL matches on, amounts, postal codes, plain mentions.
NEGATIVES = [
    "Call +91 98765 43210 now",
    "Call 9876543210 or 09876543210",
    "Number +919876543210 and 919876543210",
    "OTP sent to +91 98765 43210",
    "Transfer 50000 rupees to verify-cbi@okhdfcbank within 30 minutes.",
    "Your PIN code is 400001",
    "pincode 400001, Mumbai",
    "An OTP will be sent to your phone.",
    "Never share passwords or PINs with anyone.",
    "Tell me your password immediately",
    "The password is required for login",
    "Account number 123456789012 IFSC HDFC0001234",
    "Date of birth 12/05/1990 and case 2026-11-17",
    "reference 1234567890123456 for the parcel",
    "UPI id fraudster@okaxis and site https://fake-cbi.example/pay",
    "Aadhaar card par illegal parcel pakda gaya",
]


@pytest.mark.parametrize("text", NEGATIVES)
def test_non_secrets_are_left_unchanged(text):
    assert redact_text(text).text == text


def test_negative_table_assumptions_hold():
    assert not luhn_valid("1234567890123456")


def test_bank_account_number_is_kept_even_if_it_passes_luhn():
    acct = make_card(random.Random(3), "5", 16)
    text = f"transfer to account number {acct} at HDFC"
    assert redact_text(text).text == text   # matching and CE-2 need payment accounts


def test_seed_scenarios_are_unchanged():
    for incident in SEED_INCIDENTS:
        for ev in incident.evidence or []:
            assert redact_text(ev.text).text == ev.text


def test_identifier_extraction_is_unaffected_by_redaction():
    text = ("Call +91 98765 43210, pay verify-cbi@okhdfcbank, see https://fake-portal.example/pay. "
            "Your OTP is 482913 and CVV 829.")
    before = {(e.entity_type, e.canonical_value) for e in extract_entities(text)}
    after = {(e.entity_type, e.canonical_value) for e in extract_entities(redact_text(text).text)}
    assert before == after
    assert ("PHONE", "+919876543210") in after


def test_only_the_secret_is_replaced():
    assert redact_text("Your OTP is 482913, do not share.").text == "Your OTP is [REDACTED:OTP], do not share."


def test_speaker_turn_replies_are_redacted_in_context():
    results = redact_turns(["Please tell me the OTP you received", "482913", "okay thanks"])
    assert results[1].text == "[REDACTED:OTP]"
    assert results[2].text == "okay thanks"


def test_redact_evidence_covers_text_turns_and_provenance():
    safe = redact_evidence(
        "OTP is 482913",
        [{"speaker": "caller", "text": "send the OTP"}, {"speaker": "victim", "text": "482913"}],
        "pasted by user, password is Hunter@2026x",
    )
    blob = repr((safe.text, safe.speaker_turns, safe.provenance))
    assert "482913" not in blob and "Hunter@2026x" not in blob
    assert safe.speaker_turns[1]["speaker"] == "victim"
    assert {e.field for e in safe.events} == {"text", "turn:1", "provenance"}


def test_property_random_secrets_never_survive():
    rng = random.Random(20261117)
    templates = [
        "Sir your OTP is {s} please tell me",
        "ok the otp {s} came on my phone",
        "mera password hai {s} aur kuch nahi",
        "UPI PIN {s} daal diya",
        "card number {s} valid",
        "pay by card {s} exp 09/28",
        "Aadhaar {s} verify karo",
        "cvv {s}",
    ]
    for i in range(400):
        kind = rng.choice(["otp", "pin", "cvv", "card", "aadhaar", "password"])
        if kind == "otp":
            secret = "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(4, 8)))
            tpl = rng.choice(templates[:2])
        elif kind == "pin":
            secret = "".join(str(rng.randint(0, 9)) for _ in range(rng.choice([4, 6])))
            tpl = templates[3]
        elif kind == "cvv":
            secret = "".join(str(rng.randint(0, 9)) for _ in range(rng.choice([3, 4])))
            tpl = templates[7]
        elif kind == "card":
            secret = make_card(rng, rng.choice(["4", "5", "37"]), rng.choice([15, 16, 19]))
            tpl = rng.choice(templates[4:6])
        elif kind == "aadhaar":
            secret = make_aadhaar(rng)
            tpl = templates[6]
        else:
            secret = "".join(rng.choice("abcXYZ019@#") for _ in range(rng.randint(6, 12))) + "7"
            tpl = templates[2]
        shown = secret
        if kind in {"otp", "card", "aadhaar"} and rng.random() < 0.5:
            shown = " ".join(secret[j:j + 4] for j in range(0, len(secret), 4))
        out = redact_text(tpl.format(s=shown)).text
        compact_out = re.sub(r"[ \-]", "", out)
        assert secret not in compact_out and shown not in out, (i, kind, tpl, shown, out)


class TestKnownLimitations:
    """Documented misses. Redaction is best effort: these assertions record what is NOT caught,
    so the README/model card can say so honestly. If one starts failing because detection
    improved, update the limitation list."""

    def test_spelled_out_digits_are_not_detected(self):
        text = "the otp is four eight two nine one three"
        assert redact_text(text).text == text

    def test_secret_without_any_cue_word_is_not_detected(self):
        text = "the number from the sms is 482913"
        assert redact_text(text).text == text

    def test_non_luhn_card_without_cue_is_not_detected(self):
        text = "use 1234 5678 9012 3456 for payment"
        assert redact_text(text).text == text

    def test_amount_like_otp_after_currency_symbol_is_not_redacted(self):
        text = "otp charge of Rs 5000"
        assert redact_text(text).text == text
