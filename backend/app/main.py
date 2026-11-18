from fastapi import FastAPI, Depends, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from contextlib import asynccontextmanager
from backend.app.core.database import engine, Base, get_db, SessionLocal
from backend.app.services.seed_service import seed_session
from backend.app.core.middleware import RequestIDMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.app.core.errors import (
    VigilException, vigil_exception_handler, generic_exception_handler,
    http_exception_handler, validation_exception_handler,
)
from backend.app.api.v1 import health, incidents, graph, associations, campaigns, scenarios, simulations
from backend.app.models.models import (
    Incident, Evidence, Utterance, Entity, Mention, Relationship, TacticEvent, Association,
    Analysis, RiskContribution, CounterEvidence, Review, Campaign, CampaignMember, Redaction,
)

# Create tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.SEED_ON_START:
        with SessionLocal() as db:
            if db.query(Incident).count() == 0:
                seed_session(db)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Cross-Channel Scam Intelligence Network — VIGIL API",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(VigilException, vigil_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.FRONTEND_ORIGIN == "*" else [settings.FRONTEND_ORIGIN],
    allow_credentials=False,  # no cookies/auth in the MVP; "*" origins are invalid with credentials
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(incidents.router, prefix="/api/v1", tags=["Incidents"])
app.include_router(graph.router, prefix="/api/v1", tags=["Graph"])
app.include_router(associations.router, prefix="/api/v1", tags=["Associations"])
app.include_router(campaigns.router, prefix="/api/v1", tags=["Campaigns"])
app.include_router(scenarios.router, prefix="/api/v1", tags=["Scenario Lab"])
app.include_router(simulations.router, prefix="/api/v1", tags=["Simulation"])


@app.delete("/api/v1/data", tags=["Settings"])
def clear_all_data(confirm: bool = Query(False), db: Session = Depends(get_db)):
    """
    Clear all local database records (§9, §12.4 Settings).
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must pass ?confirm=true to erase all local data"
        )
    # Erase in reverse dependency order
    db.query(RiskContribution).delete()
    db.query(Analysis).delete()
    db.query(CounterEvidence).delete()
    db.query(Review).delete()
    db.query(Association).delete()
    db.query(CampaignMember).delete()
    db.query(Campaign).delete()
    db.query(Redaction).delete()
    db.query(TacticEvent).delete()
    db.query(Relationship).delete()
    db.query(Mention).delete()
    db.query(Entity).delete()
    db.query(Utterance).delete()
    db.query(Evidence).delete()
    db.query(Incident).delete()
    db.commit()
    return {"status": "ok", "message": "All local data has been erased successfully"}
