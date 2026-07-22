from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Criticality, OperationalStatus


class EquipmentBase(BaseModel):
    equipment_tag: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=255)
    equipment_class: str | None = None
    site: str | None = None
    system: str | None = None
    criticality: Criticality = Criticality.MEDIUM
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    operational_status: OperationalStatus = OperationalStatus.UNKNOWN
    description: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentRead(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class EquipmentListResponse(BaseModel):
    items: list[EquipmentRead]
    total: int
