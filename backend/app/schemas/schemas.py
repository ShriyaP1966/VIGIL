from dataclasses import replace
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, PrivateAttr, model_validator

from ai_engine.privacy.redaction import RedactionEvent, redact_evidence, redact_text


class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str = "offline"
    version: str = "3.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


MAX_EVIDENCE_CHARS = 20_000
MAX_SPEAKER_TURNS = 200

EvidenceType = Literal["transcript", "message", "url", "payment_request"]
SourceChannel = Literal["call", "sms", "email", "web"]
LanguageCode = Literal["en", "hi", "hi-Latn", "mr", "mixed"]


SANITISE_FAILED = "The submission could not be sanitised, so nothing was stored."


class EvidenceCreate(BaseModel):
    type: EvidenceType = "transcript"
    text: str = Field(min_length=1, max_length=MAX_EVIDENCE_CHARS)
    timestamp: Optional[datetime] = None
    provenance: Optional[str] = Field(default="user_paste", max_length=255)
    speaker_turns: Optional[List[Dict[str, Any]]] = Field(default=None, max_length=MAX_SPEAKER_TURNS)

    # Redaction events recorded by the validator below (never serialised, never sent by clients).
    _redactions: List[RedactionEvent] = PrivateAttr(default_factory=list)

    @model_validator(mode="after")
    def _redact_secrets(self):
        """Schema-boundary redaction (§5.5): runs before any service, DB, log or extractor sees the text.
        Fails closed: if redaction itself errors, the request is rejected and nothing is stored."""
        try:
            safe = redact_evidence(self.text, self.speaker_turns, self.provenance)
        except Exception:
            raise ValueError(SANITISE_FAILED) from None
        self.text = safe.text
        self.speaker_turns = safe.speaker_turns
        self.provenance = safe.provenance
        self._redactions = list(safe.events)
        return self


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_channel: SourceChannel = "call"
    language: LanguageCode = "en"
    notes: Optional[str] = Field(default=None, max_length=2000)
    scenario_id: Optional[str] = Field(default=None, max_length=100)
    evidence: Optional[List[EvidenceCreate]] = Field(default=None, max_length=20)

    _redactions: List[RedactionEvent] = PrivateAttr(default_factory=list)

    @model_validator(mode="after")
    def _redact_secrets(self):
        try:
            events: List[RedactionEvent] = []
            title = redact_text(self.title)
            self.title = title.text
            events += [replace(e, field="title") for e in title.events]
            if self.notes:
                notes = redact_text(self.notes)
                self.notes = notes.text
                events += [replace(e, field="notes") for e in notes.events]
        except Exception:
            raise ValueError(SANITISE_FAILED) from None
        self._redactions = events
        return self


class EntityMentionSchema(BaseModel):
    id: int
    type: str
    canonical_value: str
    display_value: str
    norm_method: str
    span_start: int
    span_end: int
    confidence: float


class RiskContributionSchema(BaseModel):
    factor: str
    evidence_ref: Optional[str] = None
    rule_version: str
    contribution: int
    effect: str  # SUPPORTING, MITIGATING
    explanation: str


class AnalysisSchema(BaseModel):
    id: int
    incident_id: int
    extractor: str
    extractor_version: str
    fallback_used: bool
    risk_score: int
    risk_band: str
    risk_version: str
    injection_flags: List[str]
    fingerprint: Dict[str, Any]
    contributions: List[RiskContributionSchema]


class EvidenceSchema(BaseModel):
    id: int
    type: str
    original_text: str
    normalised_text: str
    sha256: str
    provenance: str
    timestamp: datetime
    entities: List[EntityMentionSchema] = []


class RedactionSummary(BaseModel):
    kind: str
    count: int


class IncidentDetailResponse(BaseModel):
    id: int
    title: str
    source_channel: str
    language: str
    status: str
    is_synthetic: bool
    created_at: datetime
    evidence_items: List[EvidenceSchema]
    analysis: Optional[AnalysisSchema] = None
    # Secrets removed before storage, by kind. Counts only: the values are never kept.
    redactions: List[RedactionSummary] = []


class IncidentListItem(BaseModel):
    id: int
    title: str
    source_channel: str
    language: str
    status: str
    risk_score: Optional[int] = None
    risk_band: Optional[str] = None
    created_at: datetime


class GraphNode(BaseModel):
    id: str
    type: str  # incident, phone, upi, email, domain, url, organisation
    label: str
    risk_band: Optional[str] = None
    details: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str  # structural, OBSERVED_MATCH, CANDIDATE_ASSOCIATION, etc.
    label: Optional[str] = None
    similarity: Optional[float] = None
    confidence: Optional[float] = None
    status: Optional[str] = None
    explanation: Optional[str] = None


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class AssociationInspectorResponse(BaseModel):
    id: int
    status: str
    match_type: str
    incidents: List[Dict[str, Any]]
    similarity: Optional[float]
    base_confidence: float
    adjusted_confidence: float
    component_scores: Dict[str, Any]
    shared_entities: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    counter_evidence: List[Dict[str, Any]]
    explanation: str
    versions: Dict[str, str]
    review: Dict[str, Any]
