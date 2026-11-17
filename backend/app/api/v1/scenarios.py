from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services import scenario_service

router = APIRouter()


class ScenarioRunRequest(BaseModel):
    # Probability that each identifier is replaced between successive incidents of a campaign (0 to 1).
    rotation: Optional[float] = Field(default=None, ge=0.0, le=1.0)


@router.get("/scenarios")
def list_scenarios():
    """The deterministic Scenario Lab scenarios (blueprint §9)."""
    return scenario_service.list_scenarios()


@router.post("/scenarios/{name}/run")
def run_scenario(name: str, payload: Optional[ScenarioRunRequest] = None):
    """Replay one scenario through the real pipeline in an isolated in-memory database and compare it with what it
    expects. Deterministic: the same name and rotation give an identical result. Never touches stored incidents."""
    if name not in scenario_service.BY_NAME:
        raise HTTPException(status_code=404, detail=f"Unknown scenario {name!r}")
    return scenario_service.run_scenario(name, payload.rotation if payload else None)
