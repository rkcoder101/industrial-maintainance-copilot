from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.schemas.health import HealthResponse, LivenessResponse
from app.services.health import build_readiness

router = APIRouter()


@router.get("/health/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
async def ready(response: Response) -> HealthResponse:
    health = await build_readiness(get_settings())
    if health.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health


@router.get("/health", response_model=HealthResponse)
async def health(response: Response) -> HealthResponse:
    return await ready(response)
