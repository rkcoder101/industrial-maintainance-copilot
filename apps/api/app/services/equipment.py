from sqlalchemy.orm import Session

from app.repositories.equipment import EquipmentRepository
from app.schemas.equipment import EquipmentListResponse, EquipmentRead


class EquipmentService:
    def __init__(self, session: Session) -> None:
        self.repository = EquipmentRepository(session)

    def list_equipment(
        self,
        *,
        site: str | None = None,
        system: str | None = None,
        criticality: str | None = None,
        operational_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EquipmentListResponse:
        items, total = self.repository.list(
            site=site,
            system=system,
            criticality=criticality,
            operational_status=operational_status,
            limit=limit,
            offset=offset,
        )
        return EquipmentListResponse(
            items=[EquipmentRead.model_validate(item) for item in items],
            total=total,
        )

    def get_equipment(self, identifier: str) -> EquipmentRead | None:
        equipment = self.repository.get_by_identifier(identifier)
        if equipment is None:
            return None
        return EquipmentRead.model_validate(equipment)
