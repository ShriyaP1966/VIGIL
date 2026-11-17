from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.schemas import GraphResponse
from backend.app.services.graph_service import build_investigation_graph

router = APIRouter()


@router.get("/graph", response_model=GraphResponse)
def api_get_graph(
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    include_rejected: bool = Query(False),
    status: Optional[str] = Query(None, description="Only association edges with this status"),
    db: Session = Depends(get_db)
):
    return build_investigation_graph(
        db, min_confidence=min_confidence, include_rejected=include_rejected, status=status
    )
