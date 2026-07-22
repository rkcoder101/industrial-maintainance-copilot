from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.assets import Equipment
from app.schemas.equipment import EquipmentCreate


class EquipmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        *,
        site: str | None = None,
        system: str | None = None,
        criticality: str | None = None,
        operational_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Equipment], int]:
        filters = []
        if site is not None:
            filters.append(Equipment.site == site)
        if system is not None:
            filters.append(Equipment.system == system)
        if criticality is not None:
            filters.append(Equipment.criticality == criticality)
        if operational_status is not None:
            filters.append(Equipment.operational_status == operational_status)

        base_query: Select[tuple[Equipment]] = select(Equipment)
        count_query = select(func.count()).select_from(Equipment)
        if filters:
            base_query = base_query.where(*filters)
            count_query = count_query.where(*filters)

        query = base_query.order_by(Equipment.equipment_tag).limit(limit).offset(offset)
        items = list(self.session.scalars(query).all())
        total = self.session.scalar(count_query) or 0
        return items, total

    def get_by_id(self, equipment_id: UUID) -> Equipment | None:
        return self.session.get(Equipment, equipment_id)

    def get_by_tag(self, equipment_tag: str) -> Equipment | None:
        query = select(Equipment).where(Equipment.equipment_tag == equipment_tag)
        return self.session.scalar(query)

    def get_by_identifier(self, identifier: str) -> Equipment | None:
        try:
            equipment_id = UUID(identifier)
        except ValueError:
            return self.get_by_tag(identifier)

        query = select(Equipment).where(
            or_(Equipment.id == equipment_id, Equipment.equipment_tag == identifier)
        )
        return self.session.scalar(query)

    def upsert_by_tag(self, payload: EquipmentCreate) -> Equipment:
        existing = self.get_by_tag(payload.equipment_tag)
        values = payload.model_dump(mode="json")
        if existing is None:
            equipment = Equipment(**values)
            self.session.add(equipment)
            return equipment

        for key, value in values.items():
            setattr(existing, key, value)
        return existing
