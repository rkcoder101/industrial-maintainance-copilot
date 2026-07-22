from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.constraints import enum_check
from app.models.enums import Criticality, OperationalStatus


class Equipment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint(enum_check("criticality", Criticality), name="ck_equipment_criticality"),
        CheckConstraint(
            enum_check("operational_status", OperationalStatus),
            name="ck_equipment_operational_status",
        ),
        Index("ix_equipment_equipment_tag", "equipment_tag", unique=True),
        Index("ix_equipment_site_system", "site", "system"),
        Index("ix_equipment_class", "equipment_class"),
        Index("ix_equipment_criticality", "criticality"),
    )

    equipment_tag: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    equipment_class: Mapped[str | None] = mapped_column(String(120), nullable=True)
    site: Mapped[str | None] = mapped_column(String(120), nullable=True)
    system: Mapped[str | None] = mapped_column(String(120), nullable=True)
    criticality: Mapped[str] = mapped_column(
        String(40), nullable=False, default=Criticality.MEDIUM.value
    )
    manufacturer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(160), nullable=True)
    operational_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=OperationalStatus.UNKNOWN.value,
    )
    description: Mapped[str | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    components: Mapped[list["Component"]] = relationship(
        back_populates="equipment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Component(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "components"
    __table_args__ = (
        UniqueConstraint("equipment_id", "component_tag", name="uq_component_equipment_tag"),
        Index("ix_components_equipment_id", "equipment_id"),
        Index("ix_components_component_type", "component_type"),
    )

    equipment_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("equipment.id", ondelete="CASCADE"),
        nullable=False,
    )
    component_tag: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    equipment: Mapped[Equipment] = relationship(back_populates="components")
