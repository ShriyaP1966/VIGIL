from ai_engine.extraction.entity_extractor import extract_entities
from ai_engine.extraction.normalisation import mask_identifier, detect_language


def test_entity_extraction_types():
    sample_text = """
    Officer Sharma from CBI calling.
    Contact: +91 9876543210 or 09876543210.
    Send payment to fraudster@okaxis or visit https://fake-cbi-portal.com/login.
    Official inquiries at contact@cbi.gov.in.
    """
    entities = extract_entities(sample_text)
    types = {e.entity_type for e in entities}
    assert "PHONE" in types
    assert "UPI_HANDLE" in types
    assert "URL" in types
    assert "DOMAIN" in types
    assert "EMAIL" in types
    assert "ORGANISATION" in types

    # Verify phone canonical normalization to E.164
    phones = [e for e in entities if e.entity_type == "PHONE"]
    assert any(p.canonical_value == "+919876543210" for p in phones)

    # Verify UPI vs Email separation
    upis = [e for e in entities if e.entity_type == "UPI_HANDLE"]
    assert any(u.canonical_value == "fraudster@okaxis" for u in upis)

    emails = [e for e in entities if e.entity_type == "EMAIL"]
    assert any(em.canonical_value == "contact@cbi.gov.in" for em in emails)


def test_url_canonicalisation_strips_punctuation_www_tracking_and_idn():
    ents = extract_entities("Go to https://www.Fake-Portal.com/login/?utm_source=sms&id=7. Thanks")
    urls = [e for e in ents if e.entity_type == "URL"]
    domains = [e for e in ents if e.entity_type == "DOMAIN"]
    assert urls[0].canonical_value == "https://fake-portal.com/login?id=7"
    assert domains[0].canonical_value == "fake-portal.com"
    assert urls[0].raw_value.endswith("id=7")  # trailing sentence period is not part of the URL

    idn = [e for e in extract_entities("https://bücher.example/x") if e.entity_type == "DOMAIN"]
    assert idn[0].canonical_value == "xn--bcher-kva.example"


def test_phone_formats_normalise_to_same_e164():
    forms = ["+91 98765 43210", "09876543210", "9876543210", "+91-9876543210"]
    canon = {e.canonical_value for f in forms for e in extract_entities(f"call {f} now") if e.entity_type == "PHONE"}
    assert canon == {"+919876543210"}


def test_short_org_aliases_need_uppercase_to_avoid_false_matches():
    assert not [e for e in extract_entities("ed and dot are ordinary words here") if e.entity_type == "ORGANISATION"]
    orgs = {e.canonical_value for e in extract_entities("Officer from ED and the DOT called") if e.entity_type == "ORGANISATION"}
    assert orgs == {"Enforcement Directorate", "Department of Telecommunications"}


def test_email_is_not_upi_and_upi_is_not_email():
    ents = extract_entities("mail help@bank.co.in or pay help@okaxis")
    assert {(e.entity_type, e.canonical_value) for e in ents if e.entity_type in {"EMAIL", "UPI_HANDLE"}} == {
        ("EMAIL", "help@bank.co.in"), ("UPI_HANDLE", "help@okaxis")}


def test_normalisation_keeps_original_hash_and_strips_zero_width():
    from ai_engine.extraction.normalisation import normalise_text, compute_sha256
    original = "pay​ to  x@okaxis‍"
    assert normalise_text(original) == "pay to x@okaxis"
    assert compute_sha256(original) != compute_sha256(normalise_text(original))  # hash is of the ORIGINAL
    assert len(compute_sha256(original)) == 64


def test_privacy_masking():
    assert mask_identifier("+919876543210", "PHONE") == "+91 98•••••10"
    assert mask_identifier("user123@okhdfc", "UPI_HANDLE") == "us•••@okhdfc"
    assert mask_identifier("support@cbi.gov.in", "EMAIL") == "su•••@cbi.gov.in"


def test_language_detection():
    assert detect_language("This is a standard English call alert.") == "en"
    assert detect_language("Aapke naam par warrant hai, turant paise bhejo.") == "hi-Latn"
    assert detect_language("तुमच्या खात्यावर तक्रार नोंदवली आहे.") == "mr"
