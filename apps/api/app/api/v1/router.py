from fastapi import APIRouter

from app.api.v1 import documents, equipment, health, ingestion

api_router = APIRouter()
api_router.routes.extend(health.router.routes)
api_router.routes.extend(equipment.router.routes)
api_router.routes.extend(ingestion.router.routes)
api_router.routes.extend(documents.router.routes)
