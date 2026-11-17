from typing import Protocol, List, Tuple, Dict, Optional
from pydantic import BaseModel, Field


class EntityMentionData(BaseModel):
    entity_type: str  # PHONE, UPI_HANDLE, EMAIL, DOMAIN, URL, ORGANISATION
    raw_value: str
    canonical_value: str
    norm_method: str
    span_start: int
    span_end: int
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class UtteranceExtractionData(BaseModel):
    utterance_idx: int
    tactic_labels: List[str]
    confidence_scores: Dict[str, float]
    evidence_spans: List[Tuple[int, int]]


class ExtractionResult(BaseModel):
    utterances: List[UtteranceExtractionData]
    entities: List[EntityMentionData]
    institution_class: str = "UNKNOWN"
    payment_channel: str = "UNKNOWN"
    detected_language: str = "en"
    extractor_name: str
    extractor_version: str
    fallback_used: bool = False


class UtteranceInput(BaseModel):
    idx: int
    speaker: str = "unknown"
    text: str
    t_start_sec: Optional[float] = None
    language: Optional[str] = "en"


class Extractor(Protocol):
    name: str
    version: str

    def analyze(self, utterances: List[UtteranceInput]) -> ExtractionResult:
        ...
