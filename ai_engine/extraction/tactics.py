"""Tactic labels, canonical stages and their weights (blueprint §5.4, §6.6, §6.9)."""

TACTIC_LABELS = [
    "AUTHORITY_IMPERSONATION", "FALSE_ALLEGATION", "THREAT_INTIMIDATION", "ISOLATION", "URGENCY",
    "FINANCIAL_DEMAND", "CREDENTIAL_REQUEST", "LEGITIMATE", "OTHER_SUSPICIOUS",
]

# Tactic label -> canonical stage of the scam playbook. CREDENTIAL is a parallel branch.
STAGE_OF_LABEL = {
    "AUTHORITY_IMPERSONATION": "AUTHORITY",
    "FALSE_ALLEGATION": "ALLEGATION",
    "THREAT_INTIMIDATION": "THREAT",
    "ISOLATION": "ISOLATION",
    "URGENCY": "URGENCY",
    "FINANCIAL_DEMAND": "DEMAND",
    "CREDENTIAL_REQUEST": "CREDENTIAL",
}

CANONICAL_STAGES = ["AUTHORITY", "ALLEGATION", "THREAT", "ISOLATION", "URGENCY", "DEMAND"]
ALL_STAGES = CANONICAL_STAGES + ["CREDENTIAL"]

# Per-stage risk weights (blueprint §6.9 F1). Priors set a priori, not learned.
STAGE_WEIGHTS = {
    "AUTHORITY": 6, "ALLEGATION": 10, "THREAT": 14, "ISOLATION": 16,
    "URGENCY": 8, "DEMAND": 18, "CREDENTIAL": 18,
}

def stage_sequence_from_labels(label_lists: list[list[str]]) -> list[str]:
    """Canonical stages in order of first appearance. `label_lists` holds the tactic labels of each
    utterance in order; stages that appear in the same utterance are ordered canonically."""
    sequence: list[str] = []
    for labels in label_lists:
        stages = {STAGE_OF_LABEL[lab] for lab in labels if lab in STAGE_OF_LABEL}
        for stage in CANONICAL_STAGES:
            if stage in stages and stage not in sequence:
                sequence.append(stage)
    return sequence


INSTITUTION_CLASSES =["CENTRAL_AGENCY", "POLICE", "BANK", "TELECOM", "COURIER_CUSTOMS", "GOVT_OTHER", "UNKNOWN"]
PAYMENT_CHANNELS = ["UPI", "BANK_TRANSFER", "CRYPTO", "GIFT_CARD", "LINK_PAYMENT", "NONE", "UNKNOWN"]

# Speakers whose turns are never scored for scam tactics (a victim cannot run the playbook).
VICTIM_SPEAKERS = {"victim", "customer", "user", "you", "me", "self", "recipient", "receiver", "target", "caller_victim"}
