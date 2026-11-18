from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services import simulation_service as svc

router = APIRouter()


class SimTurn(BaseModel):
    speaker: str = Field(default="caller", max_length=20)
    text: str = Field(min_length=1, max_length=svc.MAX_TURN_CHARS)


class SimAnalyzeRequest(BaseModel):
    utterances: List[SimTurn] = Field(min_length=1, max_length=svc.MAX_TURNS)
    language: Optional[str] = "en"


@router.get("/simulations")
def list_simulations():
    """The scripted, synthetic call transcripts (blueprint §12.4). Text only: there is no audio and no real call."""
    return svc.list_scripts()


@router.post("/simulations/live-call/analyze")
def analyze_simulated_call(payload: SimAnalyzeRequest):
    """Analyse a progressive transcript window and return stage, risk, guidance and flags. A SIMULATION: it
    accepts text only, stores nothing and never touches the application database."""
    try:
        return svc.analyze_window([t.model_dump() for t in payload.utterances], payload.language or "en")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
