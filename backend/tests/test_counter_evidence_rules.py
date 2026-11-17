"""Counter-evidence rules CE-1..CE-7 as pure functions: one positive and one negative case per rule."""
import json

import pytest

from ai_engine.counter_evidence.public_identifiers import DEFAULT_PATH, PublicIdentifiers, get_public_identifiers
from ai_engine.counter_evidence.rules import (
    CONFIG_PATH, PairContext, PaymentHandle, SharedIdentifier, adjusted_confidence, ce1_incompatible_chronology,
    ce2_different_payment_destination, ce3_benign_context_identifier, ce4_weak_entity_extraction,
    ce5_inconsistent_impersonation, ce7_language_difference, evaluate_pair, has_high_severity, load_config,
)
from ai_engine.extraction.entity_extractor import extract_entities
from ai_engine.fingerprint.similarity import Fingerprint

CFG = load_config()
FWD = ("AUTHORITY", "ISOLATION", "URGENCY", "DEMAND")
REV = tuple(reversed(FWD))


def fp(seq=FWD, inst="CENTRAL_AGENCY", pay="UPI", lang="en"):
    return Fingerprint(sequence=tuple(seq), institution_class=inst, payment_channel=pay, language=lang)


def ctx(**kw):
    base = dict(incident_a=1, incident_b=2, fp_a=fp(), fp_b=fp())
    base.update(kw)
    return PairContext(**base)


def shared(type_="PHONE", canonical="+919876511111", display="+91 98•••••11", conf=0.98):
    return SharedIdentifier(type_, canonical, display, ({"evidence_id": 1, "incident_id": 1, "excerpt": "x"},), conf)


def handle(value, incident):
    return PaymentHandle(value, value[:2] + "•••", 10 + incident, incident)


# ---------------------------------------------------------------------------------------------
# Configuration matches the blueprint
# ---------------------------------------------------------------------------------------------

def test_rule_table_matches_the_blueprint():
    rules = {r["id"]: r for r in CFG["rules"]}
    assert {k: (v["kind"], v["severity"], v["confidence_impact"]) for k, v in rules.items()} == {
        "CE-1": ("INCOMPATIBLE_CHRONOLOGY", "HIGH", -0.30),
        "CE-2": ("DIFFERENT_PAYMENT_DESTINATION", "MEDIUM", -0.10),
        "CE-3": ("BENIGN_CONTEXT_IDENTIFIER", "HIGH", -0.40),
        "CE-4": ("WEAK_ENTITY_EXTRACTION", "MEDIUM", -0.15),
        "CE-5": ("INCONSISTENT_IMPERSONATION", "MEDIUM", -0.10),
        "CE-6": ("SINGLE_WEAK_SIGNAL", "MEDIUM", -0.15),
        "CE-7": ("LANGUAGE_DIFFERENCE", "LOW", -0.02),
        "CE-8": ("TEMPORAL_GAP", "LOW", -0.10),
    }
    assert rules["CE-6"]["status"] == "deferred" and rules["CE-8"]["status"] == "deferred"
    assert rules["CE-1"]["params"] == {"min_shared_stages": 3, "max_order_consistency": 0.6}
    assert CONFIG_PATH.exists() and DEFAULT_PATH.exists()


# ---------------------------------------------------------------------------------------------
# CE-1 incompatible chronology
# ---------------------------------------------------------------------------------------------

def test_ce1_fires_for_the_same_stages_in_conflicting_order():
    (f,) = ce1_incompatible_chronology(ctx(fp_a=fp(FWD), fp_b=fp(REV)), CFG)
    assert (f.rule_id, f.severity, f.confidence_impact) == ("CE-1", "HIGH", -0.30)
    assert "4 shared stages" in f.observation and "0%" in f.observation
    assert f.explanation and f.rule_version == "ce@3.1.0"


def test_ce1_stays_quiet_for_consistent_order_few_shared_stages_or_mild_disorder():
    assert ce1_incompatible_chronology(ctx(fp_a=fp(FWD), fp_b=fp(FWD)), CFG) == []
    assert ce1_incompatible_chronology(ctx(fp_a=fp(("AUTHORITY", "DEMAND")), fp_b=fp(("DEMAND", "AUTHORITY"))), CFG) == []
    # 2 of 3 pairs agree (0.67 >= 0.6): not conflicting enough
    assert ce1_incompatible_chronology(ctx(fp_a=fp(("AUTHORITY", "THREAT", "URGENCY")),
                                           fp_b=fp(("AUTHORITY", "URGENCY", "THREAT"))), CFG) == []


# ---------------------------------------------------------------------------------------------
# CE-2 different payment destination
# ---------------------------------------------------------------------------------------------

def test_ce2_fires_when_a_shared_contact_point_pays_into_different_handles():
    c = ctx(shared=(shared(),), handles_a=(handle("alpha11@okaxis", 1),), handles_b=(handle("beta22@oksbi", 2),))
    (f,) = ce2_different_payment_destination(c, CFG)
    assert (f.rule_id, f.severity, f.confidence_impact) == ("CE-2", "MEDIUM", -0.10)
    assert "different handles" in f.observation and len(f.evidence_refs) == 2


def test_ce2_stays_quiet_with_a_common_handle_a_missing_handle_or_no_contact_anchor():
    same = ctx(shared=(shared(),), handles_a=(handle("alpha11@okaxis", 1),),
               handles_b=(handle("alpha11@okaxis", 2), handle("beta22@oksbi", 2)))
    assert ce2_different_payment_destination(same, CFG) == []
    assert ce2_different_payment_destination(ctx(shared=(shared(),), handles_a=(handle("a1@ybl", 1),)), CFG) == []
    upi_only = ctx(shared=(shared("UPI_HANDLE", "x@ybl", "x•••@ybl"),),
                   handles_a=(handle("a1@ybl", 1),), handles_b=(handle("b2@ybl", 2),))
    assert ce2_different_payment_destination(upi_only, CFG) == []          # a UPI handle is not a contact anchor


# ---------------------------------------------------------------------------------------------
# CE-3 benign-context identifier
# ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("type_,canonical,display", [
    ("PHONE", "1930", "1930"),
    ("DOMAIN", "cybercrime.gov.in", "cybercrime.gov.in"),
    ("DOMAIN", "netbanking.sbi.co.in", "netbanking.sbi.co.in"),          # subdomain of an allowlisted domain
])
def test_ce3_fires_for_public_identifiers(type_, canonical, display):
    (f,) = ce3_benign_context_identifier(ctx(shared=(shared(type_, canonical, display),)), CFG)
    assert (f.rule_id, f.severity, f.confidence_impact) == ("CE-3", "HIGH", -0.40)
    assert "public identifier" in f.observation and f.evidence_refs


def test_ce3_fires_when_the_identifier_appears_in_a_legitimate_incident():
    c = ctx(shared=(shared("UPI_HANDLE", "pay@oksbi", "pa•••@oksbi"),), legitimate={1: False, 2: True})
    (f,) = ce3_benign_context_identifier(c, CFG)
    assert "labelled legitimate (INC-0002)" in f.observation


def test_ce3_stays_quiet_for_ordinary_identifiers_and_lookalike_domains():
    assert ce3_benign_context_identifier(ctx(shared=(shared("UPI_HANDLE", "pay@oksbi", "pa•••@oksbi"),)), CFG) == []
    assert ce3_benign_context_identifier(ctx(shared=(shared("DOMAIN", "sbi.co.in.evil.example", "x"),)), CFG) == []
    assert ce3_benign_context_identifier(ctx(shared=(shared("PHONE", "+919876511111", "x"),),
                                             legitimate={1: False, 2: False}), CFG) == []
    assert ce3_benign_context_identifier(ctx(shared=()), CFG) == []        # behaviour-only link: nothing shared


# ---------------------------------------------------------------------------------------------
# CE-4 weak entity extraction (minimal)
# ---------------------------------------------------------------------------------------------

def test_ce4_fires_only_for_low_confidence_extraction():
    (f,) = ce4_weak_entity_extraction(ctx(shared=(shared(conf=0.5),)), CFG)
    assert (f.rule_id, f.severity, f.confidence_impact) == ("CE-4", "MEDIUM", -0.15)
    assert ce4_weak_entity_extraction(ctx(shared=(shared(conf=0.95),)), CFG) == []
    assert ce4_weak_entity_extraction(ctx(shared=(shared(conf=0.7),)), CFG) == []     # boundary: not below 0.7


# ---------------------------------------------------------------------------------------------
# CE-5 inconsistent impersonation
# ---------------------------------------------------------------------------------------------

def test_ce5_fires_when_claimed_institutions_differ():
    (f,) = ce5_inconsistent_impersonation(ctx(fp_a=fp(inst="CENTRAL_AGENCY"), fp_b=fp(inst="TELECOM")), CFG)
    assert (f.rule_id, f.severity, f.confidence_impact) == ("CE-5", "MEDIUM", -0.10)
    assert "Central Agency" in f.observation and "Telecom" in f.observation


def test_ce5_stays_quiet_when_equal_or_unknown():
    assert ce5_inconsistent_impersonation(ctx(fp_a=fp(inst="POLICE"), fp_b=fp(inst="POLICE")), CFG) == []
    assert ce5_inconsistent_impersonation(ctx(fp_a=fp(inst="UNKNOWN"), fp_b=fp(inst="POLICE")), CFG) == []


# ---------------------------------------------------------------------------------------------
# CE-7 language difference (context only)
# ---------------------------------------------------------------------------------------------

def test_ce7_records_a_language_difference_as_low_severity_context():
    (f,) = ce7_language_difference(ctx(fp_a=fp(lang="en"), fp_b=fp(lang="hi-Latn")), CFG)
    assert (f.rule_id, f.severity, f.confidence_impact) == ("CE-7", "LOW", -0.02)
    assert "context only" in f.explanation


def test_ce7_stays_quiet_for_same_or_unknown_language():
    assert ce7_language_difference(ctx(fp_a=fp(lang="en"), fp_b=fp(lang="en")), CFG) == []
    assert ce7_language_difference(ctx(fp_a=fp(lang=None), fp_b=fp(lang="en")), CFG) == []


# ---------------------------------------------------------------------------------------------
# Combination, confidence adjustment, determinism
# ---------------------------------------------------------------------------------------------

def test_only_high_findings_dispute_and_low_medium_ones_do_not():
    medium_low = evaluate_pair(ctx(fp_a=fp(inst="POLICE", lang="en"), fp_b=fp(inst="TELECOM", lang="hi-Latn")), CFG)
    assert [f.rule_id for f in medium_low] == ["CE-5", "CE-7"] and not has_high_severity(medium_low)
    high = evaluate_pair(ctx(fp_a=fp(FWD), fp_b=fp(REV)), CFG)
    assert [f.rule_id for f in high] == ["CE-1"] and has_high_severity(high)


def test_adjusted_confidence_is_base_plus_impacts_clipped_to_unit_interval():
    findings = evaluate_pair(ctx(fp_a=fp(inst="POLICE", lang="en"), fp_b=fp(inst="TELECOM", lang="hi-Latn")), CFG)
    assert adjusted_confidence(0.75, findings) == pytest.approx(0.75 - 0.10 - 0.02)
    assert adjusted_confidence(0.20, evaluate_pair(ctx(shared=(shared("PHONE", "1930", "1930"),)), CFG)) == 0.0
    assert adjusted_confidence(0.9, []) == 0.9
    assert adjusted_confidence(1.0, []) == 1.0


def test_evaluation_is_deterministic_and_ordered_by_rule_id():
    c = ctx(fp_a=fp(FWD, inst="POLICE", lang="en"), fp_b=fp(REV, inst="TELECOM", lang="hi-Latn"),
            shared=(shared("PHONE", "1930", "1930", conf=0.5),))
    first = evaluate_pair(c, CFG)
    assert first == evaluate_pair(c, CFG)
    ids = [f.rule_id for f in first]
    assert ids == sorted(ids) and {"CE-1", "CE-3", "CE-4", "CE-5", "CE-7"} == set(ids)


# ---------------------------------------------------------------------------------------------
# Public identifier allowlist and the helpline extraction that feeds CE-3
# ---------------------------------------------------------------------------------------------

def test_allowlist_loads_and_matches_exactly_or_by_subdomain_only():
    public = get_public_identifiers()
    assert public.lookup("PHONE", "1930")["description"].startswith("National Cyber Crime")
    assert public.lookup("DOMAIN", "sbi.co.in") and public.lookup("DOMAIN", "login.sbi.co.in")
    assert public.lookup("URL", "https://www.cybercrime.gov.in/report")      # www. is a subdomain of the entry
    assert public.lookup("URL", "https://cybercrime.gov.in/report")
    assert public.lookup("DOMAIN", "sbi.co.in.evil.example") is None
    assert public.lookup("DOMAIN", "notsbi.co.in") is None
    assert public.lookup("PHONE", "+919876511111") is None
    assert PublicIdentifiers([{"type": "PHONE", "canonical": "112", "description": "x"}]).lookup("PHONE", "112")


def test_every_allowlist_entry_is_well_formed():
    data = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
    for e in data["identifiers"]:
        assert e["type"] in {"PHONE", "DOMAIN"} and e["canonical"] == e["canonical"].lower() and e["description"]


@pytest.mark.parametrize("text", [
    "call the official national helpline 1930 for help",
    "Cyber crime helpline 1930.",
    "Please dial 1930 immediately",
    "toll free 1930",
])
def test_the_public_helpline_is_extracted_unmasked(text):
    (e,) = [x for x in extract_entities(text) if x.entity_type == "PHONE"]
    assert (e.canonical_value, e.norm_method) == ("1930", "public_shortcode")


@pytest.mark.parametrize("text", [
    "He was born in 1930.", "Pay 1930 rupees now", "Call me and pay 1930 rupees", "helpline 19301",
    "Call +91 98765 43210",
])
def test_a_bare_number_is_not_mistaken_for_the_helpline(text):
    assert all(e.canonical_value != "1930" for e in extract_entities(text))
