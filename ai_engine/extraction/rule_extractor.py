"""Rule-based tactic extractor (blueprint §6.3 Tier 1; the ML and Gemini tiers were cut for the deadline).

Offline and deterministic: regex rules from data/lexicon.json, matched on a normalised view of each
utterance (NFKC, zero-width characters removed). Every label comes with the exact span(s) that fired,
mapped back to the original utterance text. Turns by a victim-like speaker are never scored, because a
victim does not run the scam playbook.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from ai_engine.extraction.entity_extractor import extract_entities
from ai_engine.extraction.interface import (
    ExtractionResult, UtteranceExtractionData, UtteranceInput,
)
from ai_engine.extraction.normalisation import detect_language, map_span, normalised_view
from ai_engine.extraction.tactics import TACTIC_LABELS, VICTIM_SPEAKERS

DEFAULT_LEXICON = Path(__file__).resolve().parents[2] / "data" / "lexicon.json"
DEFAULT_THRESHOLD = 0.5  # a label fires when its best rule confidence is >= this


_URL = re.compile(r"https?://\S+", re.IGNORECASE)


def _mask_urls(norm: str) -> str:
    """Blank out URLs (same length) so words inside a domain or path, e.g. 'duty-pay-748.example', are
    never read as tactic cues. The URL itself is still extracted as an entity elsewhere."""
    return _URL.sub(lambda m: "x" * len(m.group()), norm)


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for s, e in sorted(spans):
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


class RuleExtractor:
    name = "rules"

    def __init__(self, lexicon_path: Path | str = DEFAULT_LEXICON, threshold: float = DEFAULT_THRESHOLD):
        lex = json.loads(Path(lexicon_path).read_text(encoding="utf-8"))
        self.lexicon_version: str = lex["version"]
        self.version = f"rules@{self.lexicon_version.split('@')[-1]}"
        self.threshold = threshold
        macros = lex.get("macros", {})

        def expand(pattern: str) -> str:
            for key, value in macros.items():
                pattern = pattern.replace(f"<<{key}>>", value)
            return pattern

        self._rules: dict[str, list[tuple[str, float, re.Pattern]]] = {
            label: [(r["id"], float(r["confidence"]), re.compile(expand(r["pattern"]), re.IGNORECASE))
                    for r in rules]
            for label, rules in lex["labels"].items()
        }
        self._institution = [(c["class"], re.compile(expand(c["pattern"]), re.IGNORECASE))
                             for c in lex["institution_cues"]]
        self._payment = [(c["channel"], re.compile(expand(c["pattern"]), re.IGNORECASE))
                         for c in lex["payment_cues"]]

    def analyze(self, utterances: list[UtteranceInput]) -> ExtractionResult:
        results: list[UtteranceExtractionData] = []
        scored_text: list[str] = []
        entities = []
        languages: set[str] = set()

        for u in utterances:
            text = u.text or ""
            norm, idx = normalised_view(text)
            raw_norm = norm              # entities are extracted from the unmasked view
            norm = _mask_urls(norm)
            if text.strip():
                languages.add(detect_language(text))
            speaker_is_victim = (u.speaker or "").strip().lower() in VICTIM_SPEAKERS

            confidence: dict[str, float] = {}
            spans: dict[str, list[tuple[int, int]]] = {}
            if not speaker_is_victim and norm:
                scored_text.append(raw_norm)   # institution / payment cues need to see URLs
                for label, rules in self._rules.items():
                    for _rid, conf, pattern in rules:
                        for m in pattern.finditer(norm):
                            if m.end() == m.start():
                                continue
                            spans.setdefault(label, []).append(map_span(idx, m.start(), m.end()))
                            confidence[label] = max(confidence.get(label, 0.0), conf)

            labels = [lab for lab in TACTIC_LABELS if confidence.get(lab, 0.0) >= self.threshold]
            merged = {lab: _merge(spans[lab]) for lab in labels}
            results.append(UtteranceExtractionData(
                utterance_idx=u.idx,
                tactic_labels=labels,
                confidence_scores={lab: confidence[lab] for lab in labels},
                evidence_spans=_merge([s for lab in labels for s in merged[lab]]),
                label_spans=merged,
            ))
            if raw_norm:
                entities.extend(extract_entities(raw_norm))

        joined = "\n".join(scored_text)
        has_demand = any(
            lab in ("FINANCIAL_DEMAND", "CREDENTIAL_REQUEST") for r in results for lab in r.tactic_labels
        )
        return ExtractionResult(
            utterances=results,
            entities=entities,
            institution_class=self._first_match(self._institution, joined, "UNKNOWN"),
            payment_channel=self._first_match(self._payment, joined, "UNKNOWN") if has_demand else "NONE",
            detected_language=(next(iter(languages)) if len(languages) == 1 else "mixed") if languages else "en",
            extractor_name=self.name,
            extractor_version=self.version,
            fallback_used=False,
        )

    @staticmethod
    def _first_match(cues: list[tuple[str, re.Pattern]], text: str, default: str) -> str:
        for name, pattern in cues:
            if pattern.search(text):
                return name
        return default


@lru_cache(maxsize=1)
def get_default_extractor() -> RuleExtractor:
    return RuleExtractor()
