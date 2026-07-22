from fastapi import APIRouter, HTTPException, Query

from app.db.session import SessionLocal
from app.schemas.equipment import EquipmentListResponse, EquipmentRead
from app.services.equipment import EquipmentService

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("/", response_model=EquipmentListResponse)
async def list_equipment(
    site: str | None = Query(default=None, max_length=120),
    system: str | None = Query(default=None, max_length=120),
    criticality: str | None = Query(default=None, max_length=40),
    operational_status: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> EquipmentListResponse:
    with SessionLocal() as session:
        return EquipmentService(session).list_equipment(
            site=site,
            system=system,
            criticality=criticality,
            operational_status=operational_status,
            limit=limit,
            offset=offset,
        )


@router.get("/{identifier}", response_model=EquipmentRead)
async def get_equipment(
    identifier: str,
) -> EquipmentRead:
    with SessionLocal() as session:
        equipment = EquipmentService(session).get_equipment(identifier)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    return equipment
