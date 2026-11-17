"""Playbook fingerprint similarity (blueprint §6.7).

Identifiers change; the script does not. Two incidents are compared by the ORDER of the playbook stages
they went through (authority -> allegation -> threat -> isolation -> urgency -> demand), with the claimed
institution class and the payment channel as supporting signals.

    lcs_sim         = LCS / max(|A|, |B|)                              strict similarity
    containment     = LCS / min(|A|, |B|)                              tolerates cut-off calls
    containment_adj = containment * min(1, min(|A|, |B|) / 4)          a short fragment cannot match strongly
    order_ok        = share of stage pairs present in both that appear in the same relative order
    seq_sim         = 0.40*lcs_sim + 0.30*containment_adj + 0.30*order_ok
    inst_match      = 1 if equal, 0.5 if either is UNKNOWN, else 0
    pay_match       = 1 if equal, 0.5 if either is NONE/UNKNOWN, else 0
    playbook_sim    = 0.65*seq_sim + 0.15*inst_match + 0.10*pay_match   (+ 0.10*dwell_sim, see below)

Dwell similarity is NOT implemented (cut for the deadline). The blueprint says to omit a missing component
and renormalise the remaining weights, so playbook_sim = (0.65*seq + 0.15*inst + 0.10*pay) / 0.90.

Gate: both incidents need >= 3 distinct stages and LCS >= 3. Only then can playbook_sim >= T_candidate
(default 0.75) yield a CANDIDATE_ASSOCIATION.

Language and communication channel are deliberately NOT inputs: cross-channel, multilingual campaigns are
expected, so a different language is context, never a contradiction. All weights are a-priori design
choices, not learned. A fingerprint can never create an OBSERVED_MATCH or ANALYST_VERIFIED association (I2).
"""

from __future__ import annotations

from dataclasses import dataclass

FINGERPRINT_VERSION = "fingerprint@3.1.0"
DEFAULT_T_CANDIDATE = 0.75

W_SEQ, W_INST, W_PAY = 0.65, 0.15, 0.10
W_TOTAL = W_SEQ + W_INST + W_PAY          # 0.90: the 0.10 dwell weight is omitted and the rest renormalised
MIN_STAGES = 3
MIN_LCS = 3


@dataclass(frozen=True)
class Fingerprint:
    """Behavioural fingerprint of one incident. `language` and `channel` are context only."""
    sequence: tuple[str, ...]
    institution_class: str = "UNKNOWN"
    payment_channel: str = "UNKNOWN"
    language: str | None = None
    channel: str | None = None

    @classmethod
    def from_json(cls, data: dict) -> "Fingerprint":
        return cls(
            sequence=tuple(data.get("stage_sequence") or ()),
            institution_class=data.get("institution_class") or "UNKNOWN",
            payment_channel=data.get("payment_channel") or "UNKNOWN",
            language=data.get("language"),
            channel=data.get("channel"),
        )


@dataclass(frozen=True)
class SimilarityResult:
    gate_passed: bool
    gate_reason: str
    lcs: int
    lcs_sim: float
    containment: float
    containment_adj: float
    order_ok: float
    seq_sim: float
    inst_match: float
    pay_match: float
    playbook_sim: float
    t_candidate: float

    @property
    def is_candidate(self) -> bool:
        """True only if the gate passed AND the similarity reaches the threshold."""
        return self.gate_passed and self.playbook_sim >= self.t_candidate

    def component_scores(self) -> dict[str, float]:
        """Component breakdown stored on the association (dwell_sim is omitted, see module docstring)."""
        return {
            "seq_sim": self.seq_sim, "lcs_sim": self.lcs_sim, "containment_adj": self.containment_adj,
            "order_ok": self.order_ok, "inst_match": self.inst_match, "pay_match": self.pay_match,
            "playbook_sim": self.playbook_sim, "lcs": float(self.lcs), "t_candidate": self.t_candidate,
        }


def lcs_length(a: tuple[str, ...] | list[str], b: tuple[str, ...] | list[str]) -> int:
    """Length of the longest common subsequence."""
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, start=1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def order_consistency(a: tuple[str, ...] | list[str], b: tuple[str, ...] | list[str]) -> float:
    """Share of stage pairs present in BOTH sequences that appear in the same relative order.
    With no shared pair: 1.0 if at least one stage is shared (nothing to contradict), else 0.0."""
    pos_b = {s: i for i, s in enumerate(b)}
    shared = [s for s in a if s in pos_b]
    pairs = [(shared[i], shared[j]) for i in range(len(shared)) for j in range(i + 1, len(shared))]
    if not pairs:
        return 1.0 if shared else 0.0
    agree = sum(1 for x, y in pairs if pos_b[x] < pos_b[y])    # `shared` follows A's order
    return agree / len(pairs)


def _institution_match(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return 0.5 if "UNKNOWN" in (a, b) else 0.0


def _payment_match(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return 0.5 if {a, b} & {"NONE", "UNKNOWN"} else 0.0


def compare(a: Fingerprint, b: Fingerprint, t_candidate: float = DEFAULT_T_CANDIDATE) -> SimilarityResult:
    """Compare two fingerprints. Symmetric and deterministic."""
    sa, sb = tuple(a.sequence), tuple(b.sequence)
    lcs = lcs_length(sa, sb)
    longest, shortest = max(len(sa), len(sb)), min(len(sa), len(sb))

    lcs_sim = lcs / longest if longest else 0.0
    containment = lcs / shortest if shortest else 0.0
    containment_adj = containment * min(1.0, shortest / 4)
    order_ok = order_consistency(sa, sb)
    seq_sim = 0.40 * lcs_sim + 0.30 * containment_adj + 0.30 * order_ok
    inst = _institution_match(a.institution_class, b.institution_class)
    pay = _payment_match(a.payment_channel, b.payment_channel)
    playbook = (W_SEQ * seq_sim + W_INST * inst + W_PAY * pay) / W_TOTAL

    if shortest < MIN_STAGES:
        gate_ok, reason = False, f"an incident has fewer than {MIN_STAGES} distinct stages"
    elif lcs < MIN_LCS:
        gate_ok, reason = False, f"the longest common stage sequence is shorter than {MIN_LCS}"
    else:
        gate_ok, reason = True, "gate passed"

    return SimilarityResult(
        gate_passed=gate_ok, gate_reason=reason, lcs=lcs, lcs_sim=lcs_sim, containment=containment,
        containment_adj=containment_adj, order_ok=order_ok, seq_sim=seq_sim, inst_match=inst, pay_match=pay,
        playbook_sim=playbook, t_candidate=t_candidate,
    )
