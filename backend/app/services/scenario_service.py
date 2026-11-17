"""Scenario Lab backend (blueprint §9, §12): deterministic, replayable synthetic scenarios.

Each scenario picks a few synthetic incidents from the frozen generator (fixed seed), replays them through the
REAL pipeline in an isolated in-memory database (the application's database is never touched) and compares the
outcome with what the scenario expects. Same scenario and same rotation give an identical result every time.
An expectation that fails is shown as a failure: a scenario documents behaviour, it is not tuned to pass.

Rotation (0..1) is the probability that each identifier is replaced between successive incidents of a campaign.
It only changes the campaign scenarios; for the others it is ignored and reported as null.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from backend.app.services.replay_service import ReplayResult, replay_records

ROOT = Path(__file__).resolve().parents[3]
SCENARIO_SEED = 7
DEFAULT_ROTATION = 0.5
ATTACKS = ROOT / "data" / "injection_attacks.json"
DISCLAIMER = ("Synthetic scenario replayed through the real pipeline in an isolated, throwaway database. "
              "A linked group is only a hypothesis for an analyst to review, not an established finding, and nothing "
              "here is evidence about a real person or organisation.")

_gen_module = None


def _generator():
    """The frozen dataset generator, loaded by path (scripts/ is not a package)."""
    global _gen_module
    if _gen_module is None:
        spec = importlib.util.spec_from_file_location("vigil_generate_dataset", ROOT / "scripts" / "generate_dataset.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _gen_module = module
    return _gen_module


# ---------------------------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Scenario:
    name: str
    title: str
    category: str                  # positive | negative | ambiguous | decoy | counter_evidence | injection
    description: str
    adjustable: bool               # does the rotation slider change it?
    build: Callable[[float], list[dict]]
    expect: Callable[["Outcome", float | None], list[dict]]


@dataclass
class Outcome:
    records: list[dict]
    result: ReplayResult
    clean_id: str | None = None        # injection scenario: the un-attacked twin

    @property
    def observed(self) -> list:
        return [e for e in self.result.edges if e.status == "OBSERVED_MATCH"]

    @property
    def candidates(self) -> list:
        return [e for e in self.result.edges if e.status == "CANDIDATE_ASSOCIATION"]

    @property
    def disputed(self) -> list:
        return [e for e in self.result.edges if e.status == "DISPUTED_ASSOCIATION"]


def _check(name: str, expected: str, actual, passed: bool | None) -> dict:
    """passed=None marks an informational line: the scenario states no requirement there."""
    return {"name": name, "expected": expected, "actual": actual, "passed": passed}


def _records(rotation: float) -> list[dict]:
    return _generator().generate(SCENARIO_SEED, rotation)


def _instance(instance_id: str) -> Callable[[float], list[dict]]:
    return lambda r: [x for x in _records(r) if x["campaign_instance_id"] == instance_id]


def _template(template_id: str, n: int) -> Callable[[float], list[dict]]:
    return lambda r: [x for x in _records(r) if x["campaign_template_id"] == template_id][:n]


def _mixed(*parts: tuple[str, int]) -> Callable[[float], list[dict]]:
    def build(r: float) -> list[dict]:
        out = []
        for template_id, n in parts:
            out += [x for x in _records(r) if x["campaign_template_id"] == template_id][:n]
        return out
    return build


def _all_in_one_hypothesis(o: Outcome) -> bool:
    ids = {x["incident_id"] for x in o.records}
    return any(ids <= set(c["members"]) for c in o.result.campaigns)


def _sharing_pairs(records: list[dict]) -> int:
    """Pairs of incidents whose texts mention the same identifier, from the generator's own annotations. An
    incident only links by identifier if its text actually mentions one (a phrasing can leave the link out)."""
    mentions = [{(m["type"], m["canonical"]) for m in x["entity_mentions"]} for x in records]
    return sum(1 for i in range(len(records)) for j in range(i + 1, len(records)) if mentions[i] & mentions[j])


def _campaign_expect(o: Outcome, rotation: float | None) -> list[dict]:
    r = DEFAULT_ROTATION if rotation is None else rotation
    expected, obs, cand = _sharing_pairs(o.records), len(o.observed), len(o.candidates)
    checks = [_check("Observed identifier links",
                     f"{expected} (the pairs whose texts mention the same identifier; rotation {r:g})",
                     obs, obs == expected)]
    if r == 1:
        checks.append(_check("Behavioural candidate links", "at least 1 (the script is still the same)", cand, cand >= 1))
    else:
        checks.append(_check("Behavioural candidate links", "informational", cand, None))
    checks.append(_check("One hypothesis holds all incidents", "not required", _all_in_one_hypothesis(o), None))
    return checks


def _quiet_expect(o: Outcome, rotation: float | None) -> list[dict]:
    """Negatives, decoys and ambiguous notes should not form any link or hypothesis."""
    return [
        _check("Observed links after counter-evidence", "0", len(o.observed), len(o.observed) == 0),
        _check("Behavioural candidate links", "0", len(o.candidates), len(o.candidates) == 0),
        _check("Campaign hypotheses", "0", len(o.result.campaigns), len(o.result.campaigns) == 0),
    ]


def _benign_identifier_expect(o: Outcome, rotation: float | None) -> list[dict]:
    return [
        _check("Observed links after counter-evidence", "0 (CE-3: the helpline is a public identifier)",
               len(o.observed), len(o.observed) == 0),
        _check("Links disputed by counter-evidence", "at least 1", len(o.disputed), len(o.disputed) >= 1),
        _check("Campaign hypotheses", "0", len(o.result.campaigns), len(o.result.campaigns) == 0),
    ]


def _injection_records(rotation: float) -> list[dict]:
    data = json.loads(ATTACKS.read_text(encoding="utf-8"))
    attack = data["attacks"][0]
    base = data["bases"][attack["base"]]
    text = f"{base} {attack['injection']}"

    def rec(iid: str, body: str) -> dict:
        return {"incident_id": iid, "scenario_type": "injection", "campaign_template_id": "INJ",
                "campaign_instance_id": None, "source_channel": "call", "language": "en",
                "timestamp": "2026-08-01",
                "utterances": [{"idx": 0, "speaker": "caller", "text": body, "t_start_sec": 0.0}]}
    return [rec("inj_clean", base), rec("inj_attacked", text)]


def _injection_expect(o: Outcome, rotation: float | None) -> list[dict]:
    flags = o.result.injection.get("inj_attacked", [])
    clean = o.result.labels.get("inj_clean", [])
    attacked = o.result.labels.get("inj_attacked", [])
    risk_c, risk_a = o.result.risk["inj_clean"]["score"], o.result.risk["inj_attacked"]["score"]
    return [
        _check("Injection flag fires on the attacked text", "yes", bool(flags), bool(flags)),
        _check("Tactic labels unchanged by the injected instruction", "same labels as the clean text",
               {"clean": clean, "attacked": attacked}, clean == attacked),
        _check("Risk is not lowered", "attacked risk >= clean risk", {"clean": risk_c, "attacked": risk_a},
               risk_a >= risk_c),
    ]


SCENARIOS: list[Scenario] = [
    Scenario("digital_arrest_cbi", "Digital arrest: central-agency impersonation", "positive",
             "Three incidents of one campaign instance (template T1). Slide the rotation to see exact-identifier "
             "links disappear while the behavioural script still links them.", True, _instance("T1-c1"), _campaign_expect),
    Scenario("digital_arrest_customs", "Digital arrest: courier / customs officer", "positive",
             "Three incidents of one instance (T2, bank-transfer demand). Phone and account rotate independently.",
             True, _instance("T2-c1"), _campaign_expect),
    Scenario("bank_kyc_link", "Bank KYC phishing link", "positive",
             "Three SMS incidents (T4) that share a look-alike domain unless it rotates.", True,
             _instance("T4-c1"), _campaign_expect),
    Scenario("courier_customs_parcel", "Courier / customs parcel demand", "positive",
             "Three incidents of one instance (T6) with a UPI payment demand and a credential request.", True,
             _instance("T6-c1"), _campaign_expect),
    Scenario("legitimate_notices", "Legitimate bank and delivery notices", "negative",
             "Genuine alerts, one-time-password warnings, delivery and card notices. None should link; several cite "
             "the same public helpline, which counter-evidence must not treat as a shared actor.", False,
             _mixed(("N1", 3), ("N2", 2), ("N3", 2), ("N4", 2)), _quiet_expect),
    Scenario("police_verification_and_family", "Police verification call and family calls", "ambiguous",
             "A genuine police verification call asks you to visit the station (no payment); family calls are benign. "
             "Authority wording alone is not a campaign.", False, _mixed(("N5", 2), ("N6", 2)), _quiet_expect),
    Scenario("awareness_notices", "Awareness notices that quote scams (decoy D1)", "decoy",
             "Public-awareness notices describe scam scripts. They quote scam wording but are not scams. This scenario "
             "documents whether a keyword extractor tells quoting from doing.", False, _template("D1", 5), _quiet_expect),
    Scenario("benign_helpline_overlap", "Benign notices citing the same official helpline (decoy D2)",
             "counter_evidence",
             "Five genuine notices share the public helpline 1930 and a cybercrime portal. Counter-evidence rule CE-3 "
             "should dispute those links.", False, _template("D2", 5), _benign_identifier_expect),
    Scenario("reversed_chronology", "Same tactics, incompatible order (decoy D3)", "decoy",
             "Scam-like calls whose stages come in a mostly reversed order. They should not look like one campaign.",
             False, _template("D3", 4), _quiet_expect),
    Scenario("vague_notes", "Vague notes with nothing to extract (decoy D4)", "ambiguous",
             "No clear stage and, where a number appears, only in words. Nothing reliable to link on.", False,
             _template("D4", 5), _quiet_expect),
    Scenario("prompt_injection", "Prompt-injection inside a scam transcript", "injection",
             "A scam transcript with an appended instruction to mark it safe, next to the clean transcript. The guard "
             "should flag it and neither the labels nor the risk may fall.", False, _injection_records, _injection_expect),
]
BY_NAME = {s.name: s for s in SCENARIOS}


# ---------------------------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------------------------

def list_scenarios() -> list[dict]:
    return [{"name": s.name, "title": s.title, "category": s.category, "description": s.description,
             "rotation_adjustable": s.adjustable, "default_rotation": DEFAULT_ROTATION if s.adjustable else None}
            for s in SCENARIOS]


def _invariants(o: Outcome) -> list[dict]:
    i1 = all(e.shared and e.match_type in ("EXACT_IDENTIFIER", "COMBINED") for e in o.observed)
    i2 = not any(e.status == "OBSERVED_MATCH" and e.match_type == "PLAYBOOK" for e in o.result.edges)
    i4 = all(c["status"] == "HYPOTHESIS_UNREVIEWED" for c in o.result.campaigns)
    return [
        _check("I1: an observed match needs exactly equal identifiers", "always", i1, i1),
        _check("I2: behaviour alone never creates an observed match", "always", i2, i2),
        _check("I4: every campaign is an unreviewed hypothesis", "always", i4, i4),
    ]


def run_scenario(name: str, rotation: float | None = None) -> dict:
    """Replay a scenario. Raises KeyError for an unknown name and ValueError for a rotation outside 0..1."""
    scenario = BY_NAME[name]
    if rotation is not None and not 0.0 <= rotation <= 1.0:
        raise ValueError("rotation must be between 0 and 1")
    used = (DEFAULT_ROTATION if rotation is None else rotation) if scenario.adjustable else None
    records = scenario.build(used if used is not None else DEFAULT_ROTATION)
    result = replay_records(records)
    outcome = Outcome(records, result)
    checks = scenario.expect(outcome, used) + _invariants(outcome)
    stages = {x["incident_id"]: x.get("expected_stage_sequence") for x in records}
    return {
        "name": scenario.name, "title": scenario.title, "category": scenario.category,
        "description": scenario.description, "rotation": used, "seed": SCENARIO_SEED,
        "incidents": [{
            "id": x["incident_id"], "channel": x["source_channel"], "language": x["language"],
            "excerpt": " ".join(u["text"] for u in x["utterances"])[:200],
            "detected_labels": result.labels.get(x["incident_id"], []),
            "risk": result.risk.get(x["incident_id"]), "injection_flags": result.injection.get(x["incident_id"], []),
            "generator_stage_sequence": stages[x["incident_id"]],
        } for x in records],
        "links": [{"a": e.a, "b": e.b, "status": e.status, "match_type": e.match_type, "shared": list(e.shared),
                   "confidence": round(e.confidence, 4)} for e in result.edges],
        "hypotheses": result.campaigns,
        "summary": {"observed_links": len(outcome.observed), "candidate_links": len(outcome.candidates),
                    "disputed_links": len(outcome.disputed), "hypotheses": len(result.campaigns)},
        "checks": checks,
        "matches_expected": all(c["passed"] for c in checks if c["passed"] is not None),
        "disclaimer": DISCLAIMER,
    }
