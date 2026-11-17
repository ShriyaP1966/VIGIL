import re
from urllib.parse import parse_qsl, urlencode, urlparse
import phonenumbers
from ai_engine.extraction.interface import EntityMentionData

# Organization Gazetteer mapping aliases to canonical organisation names
ORG_GAZETTEER = {
    # Central Agencies
    "cbi": ("Central Bureau of Investigation", "CENTRAL_AGENCY"),
    "central bureau of investigation": ("Central Bureau of Investigation", "CENTRAL_AGENCY"),
    "ed": ("Enforcement Directorate", "CENTRAL_AGENCY"),
    "enforcement directorate": ("Enforcement Directorate", "CENTRAL_AGENCY"),
    "ncb": ("Narcotics Control Bureau", "CENTRAL_AGENCY"),
    "narcotics control bureau": ("Narcotics Control Bureau", "CENTRAL_AGENCY"),
    "nia": ("National Investigation Agency", "CENTRAL_AGENCY"),
    "national investigation agency": ("National Investigation Agency", "CENTRAL_AGENCY"),
    
    # Police / Cyber
    "cyber crime": ("Cyber Crime Cell", "POLICE"),
    "cyber cell": ("Cyber Crime Cell", "POLICE"),
    "cyber police": ("Cyber Crime Cell", "POLICE"),
    "mumbai police": ("Mumbai Police", "POLICE"),
    "delhi police": ("Delhi Police", "POLICE"),
    "state police": ("State Police", "POLICE"),
    
    # Govt / Regulators
    "trai": ("Telecom Regulatory Authority of India", "TELECOM"),
    "telecom regulatory authority of india": ("Telecom Regulatory Authority of India", "TELECOM"),
    "dot": ("Department of Telecommunications", "TELECOM"),
    "department of telecommunications": ("Department of Telecommunications", "TELECOM"),
    "rbi": ("Reserve Bank of India", "BANK"),
    "reserve bank of india": ("Reserve Bank of India", "BANK"),
    "customs": ("Indian Customs", "COURIER_CUSTOMS"),
    "customs department": ("Indian Customs", "COURIER_CUSTOMS"),
    
    # Couriers
    "fedex": ("FedEx", "COURIER_CUSTOMS"),
    "dhl": ("DHL", "COURIER_CUSTOMS"),
    "blue dart": ("Blue Dart", "COURIER_CUSTOMS"),
    "india post": ("India Post", "COURIER_CUSTOMS"),
    
    # Banks
    "sbi": ("State Bank of India", "BANK"),
    "state bank of india": ("State Bank of India", "BANK"),
    "hdfc": ("HDFC Bank", "BANK"),
    "hdfc bank": ("HDFC Bank", "BANK"),
    "icici": ("ICICI Bank", "BANK"),
    "icici bank": ("ICICI Bank", "BANK"),
    "axis bank": ("Axis Bank", "BANK"),
    "pnb": ("Punjab National Bank", "BANK"),
}

ORG_CLASS_BY_CANONICAL = {canonical: inst for canonical, inst in ORG_GAZETTEER.values()}

_URL_RE = re.compile(r"https?://[^\s<>\"'`]+", re.IGNORECASE)
_URL_TRAILING_PUNCT = ".,;:!?)]}'\""
_TRACKING_PARAMS = {"fbclid", "gclid", "msclkid", "igshid", "mc_cid", "mc_eid"}


def canonical_host(host: str) -> str:
    """Lower-case, strip 'www.' and a trailing dot, and convert IDN hosts to punycode."""
    host = host.strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return ""
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    return host


def canonical_url(scheme: str, host: str, path: str, query: str) -> str:
    """Canonical URL: scheme://host/path[?query] with tracking parameters removed."""
    path = path.rstrip("/")
    kept = sorted(
        (k, v) for k, v in parse_qsl(query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    )
    qs = f"?{urlencode(kept)}" if kept else ""
    return f"{scheme.lower()}://{host}{path}{qs}"


# Standard email TLDs to differentiate email from UPI
COMMON_EMAIL_TLDS = {
    "com", "org", "net", "edu", "gov", "mil", "in", "co.in", "io", "ai",
    "co", "info", "biz", "me", "online", "xyz", "live", "outlook"
}


def extract_entities(text: str) -> list[EntityMentionData]:
    """
    Offline entity extractor for:
    - PHONE (phonenumbers IN -> E.164)
    - UPI_HANDLE (excluding emails)
    - EMAIL
    - URL / DOMAIN
    - ORGANISATION (gazetteer)
    """
    if not text:
        return []

    entities: list[EntityMentionData] = []
    seen_canonical = set()

    # 1. Extract Phone Numbers using phonenumbers
    try:
        for match in phonenumbers.PhoneNumberMatcher(text, "IN"):
            phone_obj = match.number
            canonical_phone = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
            raw = match.raw_string
            start = match.start
            end = match.end
            if canonical_phone not in seen_canonical:
                seen_canonical.add(canonical_phone)
                entities.append(EntityMentionData(
                    entity_type="PHONE",
                    raw_value=raw,
                    canonical_value=canonical_phone,
                    norm_method="phonenumbers_E164",
                    span_start=start,
                    span_end=end,
                    confidence=0.98
                ))
    except Exception:
        pass

    # 2. Extract URLs and Domains (parse only; URLs are NEVER fetched)
    for match in _URL_RE.finditer(text):
        raw_url = match.group(0)
        start = match.start()
        # Sentence punctuation is not part of the URL.
        while raw_url and raw_url[-1] in _URL_TRAILING_PUNCT:
            raw_url = raw_url[:-1]
        end = start + len(raw_url)
        try:
            parsed = urlparse(raw_url)
            host = canonical_host(parsed.hostname or "")
            if not host:
                continue
            clean_url = canonical_url(parsed.scheme, host, parsed.path, parsed.query)

            if clean_url not in seen_canonical:
                seen_canonical.add(clean_url)
                entities.append(EntityMentionData(
                    entity_type="URL",
                    raw_value=raw_url,
                    canonical_value=clean_url,
                    norm_method="urllib_parse_stripped",
                    span_start=start,
                    span_end=end,
                    confidence=0.95
                ))

            if host and host not in seen_canonical:
                seen_canonical.add(host)
                entities.append(EntityMentionData(
                    entity_type="DOMAIN",
                    raw_value=host,
                    canonical_value=host,
                    norm_method="registered_host_lower",
                    span_start=start,
                    span_end=end,
                    confidence=0.95
                ))
        except Exception:
            pass

    # 3. Extract Emails & UPI Handles
    at_regex = re.compile(r"\b([A-Za-z0-9.\-_]{2,256})@([A-Za-z0-9.\-]{2,64})\b")
    for match in at_regex.finditer(text):
        raw_at = match.group(0)
        user = match.group(1).lower()
        domain_part = match.group(2).lower()
        start, end = match.span()

        # Check if domain has a dot with standard email TLD
        is_email = False
        if "." in domain_part:
            tld = domain_part.rsplit(".", 1)[1]
            if tld in COMMON_EMAIL_TLDS:
                is_email = True

        if is_email:
            canonical_email = f"{user}@{domain_part}"
            if canonical_email not in seen_canonical:
                seen_canonical.add(canonical_email)
                entities.append(EntityMentionData(
                    entity_type="EMAIL",
                    raw_value=raw_at,
                    canonical_value=canonical_email,
                    norm_method="lower_case",
                    span_start=start,
                    span_end=end,
                    confidence=0.95
                ))
        else:
            # UPI Handle (e.g. user@okhdfcbank, user@sbi, 9876543210@paytm)
            canonical_upi = f"{user}@{domain_part}"
            if canonical_upi not in seen_canonical:
                seen_canonical.add(canonical_upi)
                entities.append(EntityMentionData(
                    entity_type="UPI_HANDLE",
                    raw_value=raw_at,
                    canonical_value=canonical_upi,
                    norm_method="lower_case",
                    span_start=start,
                    span_end=end,
                    confidence=0.95
                ))

    # 4. Extract Claimed Organisations from Gazetteer.
    # Short aliases (ED, DOT, CBI, SBI...) must appear in upper case in the text so that
    # ordinary words such as "ed" or "dot" do not create organisation mentions.
    lower_text = text.lower()
    for alias, (canonical_name, inst_class) in ORG_GAZETTEER.items():
        if len(alias) <= 4:
            pattern = r"\b" + re.escape(alias.upper()) + r"\b"
            haystack = text
        else:
            pattern = r"\b" + re.escape(alias) + r"\b"
            haystack = lower_text
        for match in re.finditer(pattern, haystack):
            start, end = match.span()
            if canonical_name not in seen_canonical:
                seen_canonical.add(canonical_name)
                entities.append(EntityMentionData(
                    entity_type="ORGANISATION",
                    raw_value=text[start:end],
                    canonical_value=canonical_name,
                    norm_method="gazetteer_alias",
                    span_start=start,
                    span_end=end,
                    confidence=0.92
                ))

    return entities
