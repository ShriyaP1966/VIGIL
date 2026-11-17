import hashlib
import unicodedata
import re


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_ZERO_WIDTH = {"​", "‌", "‍", "⁠", "﻿", "­"}


def normalised_view(text: str) -> tuple[str, list[int]]:
    """Matching view of `text`: NFKC, zero-width characters removed, non-ASCII decimal digits
    (Devanagari, fullwidth...) mapped to ASCII. Returns (view, index_map) where index_map[i] is the
    position in the ORIGINAL text of view[i], so spans found in the view can be mapped back."""
    chars: list[str] = []
    idx: list[int] = []
    for i, ch in enumerate(text):
        if ch in _ZERO_WIDTH:
            continue
        if ch.isdecimal() and not ch.isascii():
            norm = str(unicodedata.decimal(ch))
        else:
            norm = unicodedata.normalize("NFKC", ch)
        for c in norm:
            chars.append(c)
            idx.append(i)
    return "".join(chars), idx


def map_span(idx: list[int], start: int, end: int) -> tuple[int, int]:
    """Map a [start, end) span of the normalised view back to the original text."""
    return idx[start], idx[end - 1] + 1


def normalise_text(text: str) -> str:
    """
    Normalise text:
    - Unicode NFKC decomposition
    - Strip zero-width characters and unusual whitespace
    - Collapse repeated whitespace
    """
    if not text:
        return ""
    # NFKC normalisation
    text = unicodedata.normalize("NFKC", text)
    # Remove zero-width characters (e.g. \u200B, \u200C, \u200D, \uFEFF)
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r\n|\r", "\n", text)
    return text.strip()


def detect_language(text: str) -> str:
    """
    Lightweight heuristic language detector (§6.1):
    en | hi | hi-Latn (romanised Hindi/Hinglish) | mr | mixed
    """
    if not text:
        return "en"

    # Devanagari script detection (Hindi / Marathi)
    devanagari_count = len(re.findall(r"[\u0900-\u097F]", text))
    total_letters = len(re.findall(r"\w", text))
    
    if total_letters > 0 and (devanagari_count / total_letters) > 0.25:
        # Check for Marathi-specific markers (e.g., ळ, किंवा, आहे)
        marathi_markers = ["आहे", "नाही", "कसा", "किंवा", "पोलीस", "खाते"]
        if any(m in text for m in marathi_markers) or "ळ" in text:
            return "mr"
        return "hi"

    # Hinglish / Romanised Hindi keyword check
    hinglish_keywords = [
        "aapke", "aapka", "karo", "kijiye", "paisa", "paise", "bhejo",
        "bol", "raha", "rahi", "hoon", "police", "giraftaar", "warrant",
        "shikayat", "darj", "turant", "kisi", "mat", "batana", "khata", "aadhaar"
    ]
    lower = text.lower()
    matches = sum(1 for kw in hinglish_keywords if re.search(r"\b" + kw + r"\b", lower))
    if matches >= 2:
        return "hi-Latn"

    return "en"


def mask_identifier(val: str, entity_type: str) -> str:
    """
    Privacy-aware display masking (§5.5):
    - Phone: +91 98•••••21
    - UPI: ab•••@bank
    - Email: j•••@domain.com
    """
    if not val:
        return val
    if entity_type == "PHONE":
        clean = val.replace(" ", "")
        if clean.startswith("+91") and len(clean) >= 12:
            return f"+91 {clean[3:5]}•••••{clean[-2:]}"
        elif len(clean) > 6:
            return clean[:4] + "•••••" + clean[-2:]
        return clean[:2] + "•••"
    elif entity_type in ("UPI_HANDLE", "EMAIL"):
        if "@" in val:
            user, domain = val.split("@", 1)
            masked_user = user[:2] + "•••" if len(user) > 2 else user[:1] + "••"
            return f"{masked_user}@{domain}"
        return val[:2] + "•••"
    elif entity_type in ("DOMAIN", "URL"):
        return val
    elif entity_type == "ORGANISATION":
        return val
    return val[:2] + "•••" if len(val) > 4 else val
