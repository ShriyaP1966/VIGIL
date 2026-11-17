"""Offline redaction of secrets at ingestion (blueprint §5.5).

VIGIL must never store OTPs, passwords, PINs, CVVs, card numbers or Aadhaar numbers. This module
replaces them with placeholders such as ``[REDACTED:OTP]`` BEFORE text is hashed, stored, logged or
sent to any extractor. It is pure Python (``re`` + ``unicodedata``): no model, no network, no API key.

What is deliberately NOT redacted: phone numbers, UPI handles, emails, domains and bank account
numbers. Those are the identifiers VIGIL matches on (observed matches, counter-evidence CE-2).

Detection is best effort and rule based. Known misses (documented in tests/test_redaction.py):
spelled-out digits, secrets with no cue word nearby, and very unusual formats.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace

REDACTOR_VERSION = "redact@1.0"

__all__ = [
    "REDACTOR_VERSION", "RedactionEvent", "RedactionResult", "RedactedEvidence",
    "redact_text", "redact_turns", "redact_evidence", "luhn_valid", "verhoeff_valid",
]


@dataclass(frozen=True)
class RedactionEvent:
    """One redaction. The span points at the placeholder in the RETURNED text; no secret is kept."""
    kind: str
    span_start: int
    span_end: int
    field: str = "text"


@dataclass(frozen=True)
class RedactionResult:
    text: str
    events: tuple[RedactionEvent, ...]


@dataclass(frozen=True)
class RedactedEvidence:
    text: str
    speaker_turns: list[dict] | None
    provenance: str | None
    events: tuple[RedactionEvent, ...]


# --------------------------------------------------------------------------------------
# Checksums
# --------------------------------------------------------------------------------------

def luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


_VD = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VP = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_valid(digits: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VD[c][_VP[i % 8][int(ch)]]
    return c == 0


# --------------------------------------------------------------------------------------
# Normalised view: detection runs on NFKC text with zero-width characters removed and
# non-ASCII decimal digits (Devanagari, fullwidth...) mapped to ASCII. An index map lets us
# redact the ORIGINAL text, so nothing outside a secret is altered.
# --------------------------------------------------------------------------------------

_ZERO_WIDTH = {"​", "‌", "‍", "⁠", "﻿", "­"}


def _normalised_view(text: str) -> tuple[str, list[int]]:
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


# --------------------------------------------------------------------------------------
# Patterns
# --------------------------------------------------------------------------------------

_I = re.IGNORECASE


def _digits(lo: int, hi: int) -> str:
    """lo..hi digits, optionally separated by single spaces/hyphens, not part of a longer number."""
    return rf"(?<!\d)(?<!\d[ \-])\d(?:[ \-]?\d){{{lo - 1},{hi - 1}}}(?!\d)(?![ \-]\d)"


OTP_CUE = (r"(?:\botp(?![a-z])|\bone[\s\-]*time[\s\-]*(?:password|passcode|pin|code)\b"
           r"|\b(?:verification|security|authentication|auth|confirmation)\s+code\b|ओटीपी)")
PIN_CUE = r"(?:\b[mt]?pin\b(?![\s\-]*code))"  # "PIN code" (postal) is not a secret
CVV_CUE = r"(?:\bcv[vc]2?\b|\bcid\b|\bcard\s+verification(?:\s+(?:value|code|number))?\b|सीवीवी)"
PASSWORD_CUE = r"(?:\b(?:password|passcode|passwd|pwd)\b|पासवर्ड)"
AADHAAR_CUE = r"(?:aadhaar|aadhar|adhar|आधार|\buid\b)"

_CARD_CTX = re.compile(r"\b(?:card|credit|debit|visa|master\s*card|rupay|amex)\b", _I)
_ACCT_CTX = re.compile(r"(?:\baccount\b|\ba/c\b|\bacct\b|\bac\s*no\b|\bifsc\b)", _I)
_CURRENCY_BEFORE = re.compile(r"(?:rs\.?|inr|₹|rupees?)\s*$", _I)

_PRIORITY = {"CARD": 0, "CARD_EXPIRY": 1, "AADHAAR": 1, "OTP": 2, "PIN": 3, "CVV": 3, "PASSWORD": 4}
_STOPWORDS = {"required", "needed", "not", "never", "a", "the", "your", "expired", "incorrect", "wrong",
              "invalid", "reset", "changed", "please", "and", "or", "to", "of", "safe", "secure"}


def _fwd(cue: str, lo: int, hi: int, gap: int) -> re.Pattern:
    return re.compile(rf"(?P<cue>{cue})(?P<gap>[^\d\n]{{0,{gap}}}?)(?P<val>{_digits(lo, hi)})", _I)


_FWD = {
    "OTP": _fwd(OTP_CUE, 4, 8, 40),
    "PIN": _fwd(PIN_CUE, 4, 6, 25),
    "CVV": _fwd(CVV_CUE, 3, 4, 25),
}
# "482913 is your OTP"
_OTP_BACK = re.compile(
    rf"(?P<val>{_digits(4, 8)})\s*(?:is\b|hai\b|है)?\s*(?:your\s+|the\s+|my\s+|aapka\s+|आपका\s+)?(?P<cue>{OTP_CUE})", _I)
_PASSWORD = re.compile(
    rf"(?P<cue>{PASSWORD_CUE})(?P<gap>[\s:=\-—]*(?:(?:is|hai)\b|है)?[\s:=\-—]*)(?P<val>[^\s,;\"'<>()\[\]]{{3,64}})", _I)
_CARD_NUMBER = re.compile(_digits(13, 19))
_EXPIRY = re.compile(
    r"[\s,;]{0,3}(?P<exp>(?:(?:exp(?:iry|\.)?|valid\s*(?:thru|till|upto))\s*:?\s*)?"
    r"(?:0[1-9]|1[0-2])\s*[/\-]\s*(?:\d{4}|\d{2})(?!\d))", _I)
_AADHAAR_FMT = re.compile(
    r"(?<!\d)(?<!\d[ \-])[2-9]\d{3}(?P<sep>[ \-])\d{4}(?P=sep)\d{4}(?!\d)(?![ \-]\d)")
_AADHAAR_CUED = re.compile(
    rf"(?P<cue>{AADHAAR_CUE})(?P<gap>[^\d\n]{{0,30}}?)"
    r"(?P<val>(?<!\d)[2-9]\d{3}[ \-]?\d{4}[ \-]?\d{4}(?!\d)(?![ \-]\d))", _I)

_REQUEST_CUES = [("OTP", re.compile(OTP_CUE, _I)), ("PIN", re.compile(PIN_CUE, _I)),
                 ("CVV", re.compile(CVV_CUE, _I)), ("PASSWORD", re.compile(PASSWORD_CUE, _I))]
_LEADING_LABEL = re.compile(r"^\s*(?:[A-Za-z][\w ]{0,20}:\s*)?")
_REPLY_DIGITS = {"OTP": (4, 8), "PIN": (3, 6), "CVV": (3, 4)}

Span = tuple[int, int, str]


def _request_kind(line: str) -> str | None:
    for kind, pat in _REQUEST_CUES:
        if pat.search(line):
            return kind
    return None


def _is_amount(norm: str, start: int) -> bool:
    return bool(_CURRENCY_BEFORE.search(norm[max(0, start - 8):start]))


def _reply_spans(line: str, base: int, kind: str) -> list[Span]:
    """A short reply on the line after someone asked for an OTP/PIN/CVV/password."""
    label = _LEADING_LABEL.match(line)
    body, off = line[label.end():], base + label.end()
    stripped = body.strip()
    if not stripped or len(stripped) > 40:
        return []
    if kind in _REPLY_DIGITS:
        lo, hi = _REPLY_DIGITS[kind]
        m = re.search(_digits(lo, hi), body)
        if m and not _is_amount(line, label.end() + m.start()):
            return [(off + m.start(), off + m.end(), kind)]
    elif kind == "PASSWORD":
        token = re.sub(r"^(?:it\s*is|it's|its|hai)\s+", "", stripped, flags=_I).rstrip(".!?")
        if re.fullmatch(r"\S{4,64}", token) and re.search(r"[A-Za-z0-9]", token) and not token.startswith("[REDACTED"):
            pos = body.find(token)
            return [(off + pos, off + pos + len(token), kind)]
    return []


def _scan(norm: str, prev_kind: str | None) -> tuple[list[Span], str | None]:
    cands: list[tuple[int, int, int, str]] = []

    def add(kind: str, s: int, e: int) -> None:
        cands.append((_PRIORITY[kind], s, e, kind))

    # Cue + digits (OTP / PIN / CVV)
    for kind, pat in _FWD.items():
        for m in pat.finditer(norm):
            if not _is_amount(norm, m.start("val")):
                add(kind, m.start("val"), m.end("val"))
    for m in _OTP_BACK.finditer(norm):
        add("OTP", m.start("val"), m.end("val"))

    # Passwords: cue + token; without an explicit separator the token must look like a secret
    for m in _PASSWORD.finditer(norm):
        val = m.group("val")
        trimmed = val.rstrip(".!?")
        if len(trimmed) < 3 or trimmed.startswith("[REDACTED") or trimmed.lower() in _STOPWORDS:
            continue
        has_sep = bool(re.search(r"[:=\-—]|\bis\b|\bhai\b|है", m.group("gap"), _I))
        if not has_sep and not (len(trimmed) >= 4 and (re.search(r"\d", trimmed) or re.search(r"[^\w]", trimmed))):
            continue
        add("PASSWORD", m.start("val"), m.start("val") + len(trimmed))

    # Card numbers: Luhn-valid, or a card cue nearby; an account cue without a card cue wins over Luhn
    for m in _CARD_NUMBER.finditer(norm):
        digits = re.sub(r"\D", "", m.group())
        if not 13 <= len(digits) <= 19:
            continue
        window = norm[max(0, m.start() - 40):m.start()]
        card_ctx, acct_ctx = bool(_CARD_CTX.search(window)), bool(_ACCT_CTX.search(window))
        if card_ctx or (luhn_valid(digits) and not acct_ctx):
            add("CARD", m.start(), m.end())
            exp = _EXPIRY.match(norm, m.end())
            if exp:
                add("CARD_EXPIRY", exp.start("exp"), exp.end("exp"))

    # Aadhaar: 4-4-4 grouping that passes Verhoeff, or a 12-digit number after an Aadhaar cue
    for m in _AADHAAR_FMT.finditer(norm):
        if verhoeff_valid(re.sub(r"\D", "", m.group())):
            add("AADHAAR", m.start(), m.end())
    for m in _AADHAAR_CUED.finditer(norm):
        add("AADHAAR", m.start("val"), m.end("val"))

    # Short replies to a request for a credential, line by line (also across speaker turns)
    offset, carry = 0, prev_kind
    for line in norm.split("\n"):
        if line.strip():
            if carry:
                for s, e, kind in _reply_spans(line, offset, carry):
                    add(kind, s, e)
            carry = _request_kind(line)
        offset += len(line) + 1

    accepted: list[Span] = []
    for _, s, e, kind in sorted(cands):
        if all(e <= a_s or s >= a_e for a_s, a_e, _ in accepted):
            accepted.append((s, e, kind))
    accepted.sort()
    return accepted, carry


def _redact(text: str, prev_kind: str | None) -> tuple[RedactionResult, str | None]:
    if not text:
        return RedactionResult(text or "", ()), prev_kind
    norm, idx = _normalised_view(text)
    spans, last_kind = _scan(norm, prev_kind)
    if not spans:
        return RedactionResult(text, ()), last_kind

    out: list[str] = []
    events: list[RedactionEvent] = []
    cursor, out_len = 0, 0
    for s, e, kind in spans:
        o_start, o_end = max(idx[s], cursor), idx[e - 1] + 1
        if o_end <= o_start:
            continue
        keep = text[cursor:o_start]
        placeholder = f"[REDACTED:{kind}]"
        out.append(keep)
        out_len += len(keep)
        events.append(RedactionEvent(kind, out_len, out_len + len(placeholder)))
        out.append(placeholder)
        out_len += len(placeholder)
        cursor = o_end
    out.append(text[cursor:])
    return RedactionResult("".join(out), tuple(events)), last_kind


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------

def redact_text(text: str) -> RedactionResult:
    """Redact one text. Idempotent: redacting the result again changes nothing."""
    return _redact(text, None)[0]


def redact_turns(texts: list[str]) -> list[RedactionResult]:
    """Redact speaker turns in order, so a short reply to "tell me the OTP" is caught."""
    results: list[RedactionResult] = []
    carry: str | None = None
    for t in texts:
        res, carry = _redact(t, carry)
        results.append(res)
    return results


def redact_evidence(text: str, speaker_turns: list[dict] | None, provenance: str | None) -> RedactedEvidence:
    """Redact every user-supplied string of one evidence item. Raises on internal error (caller fails closed)."""
    events: list[RedactionEvent] = []
    main = redact_text(text)
    events += [replace(e, field="text") for e in main.events]

    new_turns: list[dict] | None = None
    if speaker_turns:
        results = redact_turns([str(t.get("text", "")) for t in speaker_turns])
        new_turns = []
        for i, (turn, res) in enumerate(zip(speaker_turns, results)):
            new_turns.append({**turn, "text": res.text})
            events += [replace(e, field=f"turn:{i}") for e in res.events]

    new_prov = provenance
    if provenance:
        pres = redact_text(provenance)
        new_prov = pres.text
        events += [replace(e, field="provenance") for e in pres.events]

    return RedactedEvidence(main.text, new_turns, new_prov, tuple(events))
