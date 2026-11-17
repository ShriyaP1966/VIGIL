from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str = "offline"
    version: str = "3.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EvidenceCreate(BaseModel):
    type: str = "transcript"  # transcript, message, url, payment_request
    text: str
    timestamp: Optional[datetime] = None
    provenance: Optional[str] = "user_paste"
    speaker_turns: Optional[List[Dict[str, Any]]] = None


class IncidentCreate(BaseModel):
    title: str
    source_channel: str = "call"  # call, sms, email, web
    language: str = "en"
    notes: Optional[str] = None
    scenario_id: Optional[str] = None
    evidence: Optional[List[EvidenceCreate]] = None


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
