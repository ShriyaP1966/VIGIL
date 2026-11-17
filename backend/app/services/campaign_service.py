"""Campaign hypotheses (blueprint §6.8). A campaign is ALWAYS a hypothesis until an analyst accepts it (I4),
and even then it stays a "hypothesis accepted by an analyst": VIGIL never presents a grouping as an
established finding and never attributes activity to a person.

Build rules
  * Edges that connect incidents: OBSERVED_MATCH and ANALYST_VERIFIED_ASSOCIATION (strong), plus
    CANDIDATE_ASSOCIATION (weaker). DISPUTED and REJECTED associations never connect incidents; they are
    listed on the hypothesis as excluded links.
  * Each connected group of >= 2 incidents is one hypothesis. Member basis: ANALYST (has a verified edge),
    else OBSERVED (has an exact-identifier edge), else CANDIDATE (behaviour only).
    Deviation from the blueprint: a group connected ONLY by candidate links is also a hypothesis (shown as
    behaviour-only), otherwise a campaign whose identifiers were all rotated could never appear.
  * confidence = mean adjusted confidence of the connecting associations; the weakest link is always shown.
  * Rebuilding keeps analyst-reviewed hypotheses and their ids stable by matching on member overlap.
"""

import json
from collections import Counter

from sqlalchemy.orm import Session

from backend.app.models.models import Analysis, Association, Campaign, CampaignMember, Incident, Review

CAMPAIGN_VERSION = "campaign@3.1.0"

STRONG = {"OBSERVED_MATCH", "ANALYST_VERIFIED_ASSOCIATION"}
CONNECTING = STRONG | {"CANDIDATE_ASSOCIATION"}
EXCLUDED = {"DISPUTED_ASSOCIATION", "REJECTED_ASSOCIATION"}

DECISION_STATUS = {"ACCEPT": "ACCEPTED_BY_ANALYST", "REJECT": "REJECTED_BY_ANALYST", "FLAG": "FLAGGED"}
STATUS_LABEL = {
    "HYPOTHESIS_UNREVIEWED": "Hypothesis (unreviewed)",
    "ACCEPTED_BY_ANALYST": "Hypothesis accepted by an analyst",
    "REJECTED_BY_ANALYST": "Hypothesis rejected by an analyst",
    "FLAGGED": "Hypothesis flagged for review",
}
BASIS_RANK = {"ANALYST": 0, "OBSERVED": 1, "CANDIDATE": 2}


def _components(edges: list[Association]) -> list[set[int]]:
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        ra, rb = find(e.incident_a_id), find(e.incident_b_id)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    groups: dict[int, set[int]] = {}
    for node in list(parent):
        groups.setdefault(find(node), set()).add(node)
    return [g for _, g in sorted(groups.items()) if len(g) >= 2]


def _basis(member: int, edges: list[Association]) -> str:
    kinds = {e.status for e in edges if member in (e.incident_a_id, e.incident_b_id)}
    if "ANALYST_VERIFIED_ASSOCIATION" in kinds:
        return "ANALYST"
    if "OBSERVED_MATCH" in kinds:
        return "OBSERVED"
    return "CANDIDATE"


def _title(db: Session, members: set[int]) -> str:
    latest: dict[int, Analysis] = {}
    for a in db.query(Analysis).filter(Analysis.incident_id.in_(members)).order_by(Analysis.id):
        latest[a.incident_id] = a
    institutions = Counter(
        json.loads(a.fingerprint_json or "{}").get("institution_class", "UNKNOWN") for a in latest.values())
    institutions.pop("UNKNOWN", None)
    hint = f" (claimed institution: {institutions.most_common(1)[0][0].replace('_', ' ').title()})" if institutions else ""
    return f"Campaign hypothesis: {len(members)} related incidents{hint}"


def rebuild_campaigns(db: Session) -> list[Campaign]:
    """Recompute hypotheses from the current associations. Deterministic and idempotent."""
    assocs = db.query(Association).order_by(Association.id).all()
    connecting = [a for a in assocs if a.status in CONNECTING]
    groups = _components(connecting)

    existing = db.query(Campaign).order_by(Campaign.id).all()
    existing_members = {c.id: {m.incident_id for m in c.members} for c in existing}
    unused = {c.id: c for c in existing}

    # Pair groups with existing campaigns by largest member overlap (greedy, deterministic)
    pairs = sorted(
        ((len(g & existing_members[cid]), -cid, gi) for gi, g in enumerate(groups) for cid in existing_members
         if g & existing_members[cid]),
        reverse=True,
    )
    assigned: dict[int, Campaign] = {}
    for _overlap, neg_cid, gi in pairs:
        cid = -neg_cid
        if gi not in assigned and cid in unused:
            assigned[gi] = unused.pop(cid)

    result: list[Campaign] = []
    for gi, members in enumerate(groups):
        edges = [e for e in connecting if e.incident_a_id in members and e.incident_b_id in members]
        weakest = min(edges, key=lambda e: (e.adjusted_confidence, e.id))
        confidence = sum(e.adjusted_confidence for e in edges) / len(edges)
        title = _title(db, members)          # computed first: querying after db.add() would autoflush a half-built row
        campaign = assigned.get(gi)
        if campaign is None:
            campaign = Campaign(status="HYPOTHESIS_UNREVIEWED", hypothesis_title=title)
            db.add(campaign)
        campaign.hypothesis_title = title
        campaign.confidence = confidence
        campaign.weakest_link_association_id = weakest.id
        campaign.algorithm_version = CAMPAIGN_VERSION
        db.flush()
        db.query(CampaignMember).filter(CampaignMember.campaign_id == campaign.id).delete()
        for incident_id in sorted(members):
            db.add(CampaignMember(campaign_id=campaign.id, incident_id=incident_id,
                                  membership_basis=_basis(incident_id, edges)))
        result.append(campaign)

    # Hypotheses nothing supports any more: drop unreviewed ones, keep analyst-reviewed ones as history
    for campaign in unused.values():
        if campaign.status == "HYPOTHESIS_UNREVIEWED":
            db.delete(campaign)
    db.commit()
    return result


def apply_campaign_review(db: Session, campaign_id: int, decision: str, note: str | None) -> Campaign:
    if decision not in DECISION_STATUS:
        raise ValueError(f"unknown decision {decision!r}")
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign is None:
        raise LookupError("Campaign not found")
    new_status = DECISION_STATUS[decision]
    db.add(Review(target_type="campaign", target_id=campaign.id, decision=decision, note=note,
                  previous_status=campaign.status, new_status=new_status))
    campaign.status = new_status
    db.commit()
    db.refresh(campaign)
    return campaign


def incident_titles(db: Session, ids: set[int]) -> dict[int, Incident]:
    return {i.id: i for i in db.query(Incident).filter(Incident.id.in_(ids)).all()} if ids else {}
