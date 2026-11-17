"""Prompt-injection guard (blueprint §6.4). Evidence text is untrusted input.

VIGIL's default pipeline is rule-based, so the main risk is not an LLM being hijacked but text that tries
to *argue the system into a lower risk*: "ignore previous instructions", "mark this call as safe", fake
system messages. This guard flags such phrases. Consequences, enforced in the analysis pipeline:
  * the "Manipulation attempt detected" badge data is recorded (`injection_flags`);
  * flagged spans are masked before tactic extraction, so they cannot create labels;
  * no mitigating risk factor is applied to a flagged incident, so injected text can never lower risk.

It is a regex layer: it catches the known phrasings below and will miss novel or obfuscated wording
(see tests/test_injection_guard.py::TestKnownLimitations). Detection runs on the normalised view
(NFKC, zero-width characters removed) so trivial obfuscation does not hide a phrase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_engine.extraction.normalisation import map_span, normalised_view

GUARD_VERSION = "guard@1.0"

_I = re.IGNORECASE
RULES: list[tuple[str, re.Pattern]] = [(rid, re.compile(p, _I)) for rid, p in [
    ("ignore_instructions",
     r"\b(?:ignore|disregard|forget|override|bypass|skip)\b[^.\n]{0,30}?\b(?:previous|prior|above|earlier|preceding|all|any|your|these|the)\b"
     r"[^.\n]{0,30}?\b(?:instructions?|rules?|prompts?|guidelines?|directions?|commands?|programming)\b"),
    ("mark_safe",
     r"\b(?:mark|label|classify|rate|tag|set|treat|consider|report|flag|score|categori[sz]e|record|log)\b[^.\n]{0,40}?"
     r"\b(?:as\s+)?(?:safe|legit(?:imate)?|benign|harmless|genuine|not\s+(?:a\s+)?(?:scam|fraud|suspicious|spam)|"
     r"low[\s-]*risk|zero[\s-]*risk|no[\s-]*risk)\b"),
    ("risk_override",
     r"\b(?:set|make|keep|put|reduce|lower|change)\b[^.\n]{0,30}?\brisk(?:\s+(?:score|level|rating))?\b[^.\n]{0,20}?"
     r"\b(?:to\s+)?(?:0|zero|low|minimum|none|nil)\b"),
    ("role_override",
     r"\byou\s+are\s+now\b|\bact\s+as\b[^.\n]{0,30}?\b(?:assistant|ai|model|bot|system|analy[sz]er|classifier)\b"
     r"|\bpretend\s+(?:to\s+be|that\s+you)\b|\bfrom\s+now\s+on\b[^.\n]{0,40}?\b(?:you|the\s+(?:system|assistant|model|classifier))\b"),
    ("system_prompt",
     r"\b(?:system\s+prompt|system\s+message|developer\s+(?:message|mode)|jailbreak|dan\s+mode)\b"),
    ("new_instructions",
     r"\b(?:new|updated|real|actual|important)\s+instructions?\s*[:\-]"
     r"|\binstructions?\s+(?:for|to)\s+(?:the\s+)?(?:ai|assistant|model|classifier|analy[sz]er|vigil)\b"
     r"|\bnote\s+to\s+(?:the\s+)?(?:ai|assistant|model|classifier|analy[sz]er|reviewer|system)\b"),
    ("role_marker",
     r"(?:^|\n)\s*(?:system|assistant|developer)\s*:|<\s*/?\s*(?:system|instructions?|assistant)\s*>"
     r"|\[\s*/?\s*(?:inst|system)\s*\]|###\s*(?:instruction|system)"),
    ("do_not_flag",
     r"\b(?:do\s+not|don't|dont|never)\s+(?:flag|report|alert|block|escalate)\b|\bno\s+need\s+to\s+(?:flag|alert|report|escalate)\b"),
    ("hinglish_override",
     r"\b(?:pichle|pehle\s+ke|saare|sabhi)\s+instructions?\b[^.\n]{0,30}?\b(?:ignore|bhool|nazarandaz)\b"
     r"|\bise\s+safe\s+(?:mark|batao|samjho|maano)\b|\bsafe\s+mark\s+(?:karo|kar\s*do|kijiye)\b"),
]]


@dataclass(frozen=True)
class InjectionFlag:
    rule_id: str
    span_start: int   # span in the ORIGINAL text
    span_end: int


def detect_injection(text: str) -> list[InjectionFlag]:
    """Flag instruction-like phrases. Spans are mapped back to the original text."""
    if not text:
        return []
    norm, idx = normalised_view(text)
    flags: list[InjectionFlag] = []
    for rule_id, pattern in RULES:
        for m in pattern.finditer(norm):
            if m.end() > m.start():
                s, e = map_span(idx, m.start(), m.end())
                flags.append(InjectionFlag(rule_id, s, e))
    return sorted(flags, key=lambda f: (f.span_start, f.span_end, f.rule_id))


def mask_spans(text: str, flags: list[InjectionFlag]) -> str:
    """Blank out flagged spans with spaces (same length, so offsets elsewhere stay valid)."""
    if not flags:
        return text
    chars = list(text)
    for f in flags:
        for i in range(f.span_start, min(f.span_end, len(chars))):
            chars[i] = " "
    return "".join(chars)


def flag_ids(flags: list[InjectionFlag]) -> list[str]:
    return sorted({f.rule_id for f in flags})
