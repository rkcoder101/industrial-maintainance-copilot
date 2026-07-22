from fastapi import APIRouter

from app.api.v1 import equipment, health

api_router = APIRouter()
api_router.routes.extend(health.router.routes)
api_router.routes.extend(equipment.router.routes)
