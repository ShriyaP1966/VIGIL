from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    source_channel = Column(String(50), default="call")  # call, sms, email, web
    language = Column(String(20), default="en")
    status = Column(String(50), default="open")          # open, reviewed
    scenario_id = Column(String(100), nullable=True)
    is_synthetic = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    evidence_items = relationship("Evidence", back_populates="incident", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="incident", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # transcript, message, url, payment_request
    original_text = Column(Text, nullable=False)
    normalised_text = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime, default=utcnow)
    provenance = Column(String(255), default="user_paste")

    incident = relationship("Incident", back_populates="evidence_items")
    utterances = relationship("Utterance", back_populates="evidence", cascade="all, delete-orphan")
    mentions = relationship("Mention", back_populates="evidence", cascade="all, delete-orphan")


class Redaction(Base):
    """Audit record that a secret was removed at ingestion (blueprint §5.5).
    Never holds the secret itself: only its kind and the placeholder's span in the stored text."""
    __tablename__ = "redactions"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=True, index=True)
    field = Column(String(50), nullable=False)  # text | turn:<n> | provenance | title | notes
    kind = Column(String(30), nullable=False)   # OTP | PIN | CVV | PASSWORD | CARD | CARD_EXPIRY | AADHAAR
    span_start = Column(Integer, default=0)
    span_end = Column(Integer, default=0)
    detector_version = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Utterance(Base):
    __tablename__ = "utterances"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False)
    idx = Column(Integer, nullable=False)
    speaker = Column(String(50), default="unknown")
    text = Column(Text, nullable=False)
    t_start_sec = Column(Float, nullable=True)
    language = Column(String(20), default="en")

    evidence = relationship("Evidence", back_populates="utterances")
    tactic_events = relationship("TacticEvent", back_populates="utterance", cascade="all, delete-orphan")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, index=True)  # PHONE, EMAIL, DOMAIN, URL, UPI_HANDLE, ORGANISATION
    canonical_value = Column(String(255), nullable=False, index=True)
    display_value = Column(String(255), nullable=False)    # Masked representation
    norm_method = Column(String(50), default="regex")
    first_seen = Column(DateTime, default=utcnow)
    last_seen = Column(DateTime, default=utcnow)

    mentions = relationship("Mention", back_populates="entity", cascade="all, delete-orphan")


class Mention(Base):
    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False)
    utterance_id = Column(Integer, ForeignKey("utterances.id", ondelete="SET NULL"), nullable=True)
    span_start = Column(Integer, default=0)
    span_end = Column(Integer, default=0)
    extraction_confidence = Column(Float, default=1.0)
    extractor = Column(String(100), default="regex@3.1.0")

    entity = relationship("Entity", back_populates="mentions")
    evidence = relationship("Evidence", back_populates="mentions")


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    relation_type = Column(String(50), nullable=False)  # MENTIONS_ENTITY, USES_PHONE, etc.
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True)
    confidence = Column(Float, default=1.0)


class Association(Base):
    __tablename__ = "associations"

    id = Column(Integer, primary_key=True, index=True)
    incident_a_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_b_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    match_type = Column(String(50), nullable=False)  # EXACT_IDENTIFIER, PLAYBOOK, FUZZY_IDENTIFIER, COMBINED
    status = Column(String(50), nullable=False, default="CANDIDATE_ASSOCIATION")
    # Statuses: OBSERVED_MATCH, CANDIDATE_ASSOCIATION, ANALYST_VERIFIED_ASSOCIATION, DISPUTED_ASSOCIATION, REJECTED_ASSOCIATION
    shared_entity_ids_json = Column(Text, default="[]")
    similarity = Column(Float, nullable=True)
    base_confidence = Column(Float, default=0.75)
    adjusted_confidence = Column(Float, default=0.75)
    component_scores_json = Column(Text, default="{}")
    supporting_evidence_json = Column(Text, default="[]")
    explanation = Column(Text, nullable=False)
    algorithm_version = Column(String(50), default="vigil@3.1.0")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    counter_evidence = relationship("CounterEvidence", back_populates="association", cascade="all, delete-orphan")


class CounterEvidence(Base):
    __tablename__ = "counter_evidence"

    id = Column(Integer, primary_key=True, index=True)
    association_id = Column(Integer, ForeignKey("associations.id", ondelete="CASCADE"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    rule_id = Column(String(50), nullable=False)  # CE-1 ... CE-8
    kind = Column(String(100), nullable=False)
    observation = Column(Text, nullable=False)
    evidence_refs_json = Column(Text, default="[]")
    severity = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH
    confidence_impact = Column(Float, default=-0.10)
    explanation = Column(Text, nullable=False)
    rule_version = Column(String(50), default="ce@3.1.0")
    created_at = Column(DateTime, default=utcnow)

    association = relationship("Association", back_populates="counter_evidence")
    campaign = relationship("Campaign", back_populates="counter_evidence")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(50), nullable=False)  # association, campaign
    target_id = Column(Integer, nullable=False, index=True)
    decision = Column(String(50), nullable=False)    # ACCEPT, REJECT, FLAG
    note = Column(Text, nullable=True)
    previous_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    hypothesis_title = Column(String(255), nullable=False)
    status = Column(String(50), default="HYPOTHESIS_UNREVIEWED")
    # Statuses: HYPOTHESIS_UNREVIEWED, ACCEPTED_BY_ANALYST, REJECTED_BY_ANALYST, FLAGGED
    confidence = Column(Float, default=0.75)
    weakest_link_association_id = Column(Integer, nullable=True)
    algorithm_version = Column(String(50), default="campaign@3.1.0")
    created_at = Column(DateTime, default=utcnow)

    members = relationship("CampaignMember", back_populates="campaign", cascade="all, delete-orphan")
    counter_evidence = relationship("CounterEvidence", back_populates="campaign", cascade="all, delete-orphan")


class CampaignMember(Base):
    __tablename__ = "campaign_members"

    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True)
    membership_basis = Column(String(50), default="OBSERVED")  # OBSERVED, CANDIDATE, ANALYST

    campaign = relationship("Campaign", back_populates="members")


class TacticEvent(Base):
    __tablename__ = "tactic_events"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    utterance_id = Column(Integer, ForeignKey("utterances.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(100), nullable=False)
    confidence = Column(Float, default=1.0)
    extractor = Column(String(100), default="rules@3.1.0")
    evidence_span = Column(String(50), default="0:0")

    utterance = relationship("Utterance", back_populates="tactic_events")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    extractor = Column(String(100), default="RuleMLExtractor")
    extractor_version = Column(String(50), default="3.1.0")
    fallback_used = Column(Boolean, default=False)
    fingerprint_json = Column(Text, default="{}")
    risk_score = Column(Integer, default=0)
    risk_band = Column(String(20), default="LOW")  # LOW, ELEVATED, HIGH, CRITICAL
    risk_version = Column(String(50), default="risk@3.1.0")
    injection_flags_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=utcnow)

    incident = relationship("Incident", back_populates="analyses")
    contributions = relationship("RiskContribution", back_populates="analysis", cascade="all, delete-orphan")


class RiskContribution(Base):
    __tablename__ = "risk_contributions"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    factor = Column(String(100), nullable=False)
    evidence_ref = Column(String(100), nullable=True)
    rule_version = Column(String(50), default="risk@3.1.0")
    contribution = Column(Integer, nullable=False)
    effect = Column(String(20), nullable=False)  # SUPPORTING, MITIGATING
    explanation = Column(Text, nullable=False)

    analysis = relationship("Analysis", back_populates="contributions")
