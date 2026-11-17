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


def test_privacy_masking():
    assert mask_identifier("+919876543210", "PHONE") == "+91 98•••••10"
    assert mask_identifier("user123@okhdfc", "UPI_HANDLE") == "us•••@okhdfc"
    assert mask_identifier("support@cbi.gov.in", "EMAIL") == "su•••@cbi.gov.in"


def test_language_detection():
    assert detect_language("This is a standard English call alert.") == "en"
    assert detect_language("Aapke naam par warrant hai, turant paise bhejo.") == "hi-Latn"
    assert detect_language("तुमच्या खात्यावर तक्रार नोंदवली आहे.") == "mr"
