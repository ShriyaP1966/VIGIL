from fastapi import APIRouter
from backend.app.schemas.schemas import HealthResponse
from backend.app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health():
    return HealthResponse(
        status="ok",
        mode=settings.APP_MODE,
        version=settings.APP_VERSION
    )
