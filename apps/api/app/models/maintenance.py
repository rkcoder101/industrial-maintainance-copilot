from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.types import Uuid

from app.db.base import Base, MetadataMixin, ProvenanceMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.constraints import enum_check
from app.models.enums import ActionStatus, ProcedureStatus, WorkOrderPriority, WorkOrderStatus


class Procedure(UUIDPrimaryKeyMixin, ProvenanceMixin, MetadataMixin, TimestampMixin, Base):
    __tablename__ = "procedures"
    __table_args__ = (
        UniqueConstraint("procedure_code", "revision", name="uq_procedures_code_revision"),
        CheckConstraint(enum_check("status", ProcedureStatus), name="ck_procedures_status"),
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_procedures_confidence",
        ),
        Index("ix_procedures_procedure_code", "procedure_code"),
        Index("ix_procedures_status", "status"),
    )

    procedure_code: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    revision: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    effective_date: Mapped[date | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=ProcedureStatus.DRAFT.value,
    )
    document_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )


class MaintenanceAction(UUIDPrimaryKeyMixin, ProvenanceMixin, MetadataMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_actions"
    __table_args__ = (
        CheckConstraint(enum_check("status", ActionStatus), name="ck_maintenance_actions_status"),
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_maintenance_actions_confidence",
        ),
        Index("ix_maintenance_actions_equipment_id", "equipment_id"),
        Index("ix_maintenance_actions_event_id", "event_id"),
        Index("ix_maintenance_actions_procedure_id", "procedure_id"),
        Index("ix_maintenance_actions_performed_at", "performed_at"),
    )

    event_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    equipment_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("equipment.id", ondelete="RESTRICT"),
        nullable=False,
    )
    component_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("components.id", ondelete="SET NULL"),
        nullable=True,
    )
    procedure_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("procedures.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    result: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=ActionStatus.UNKNOWN.value
    )


class WorkOrder(UUIDPrimaryKeyMixin, ProvenanceMixin, MetadataMixin, TimestampMixin, Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        UniqueConstraint("work_order_number", name="uq_work_orders_number"),
        CheckConstraint(enum_check("priority", WorkOrderPriority), name="ck_work_orders_priority"),
        CheckConstraint(enum_check("status", WorkOrderStatus), name="ck_work_orders_status"),
        CheckConstraint(
            "completed_at is null or opened_at is null or completed_at >= opened_at",
            name="ck_work_orders_time_order",
        ),
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_work_orders_confidence",
        ),
        Index("ix_work_orders_equipment_id", "equipment_id"),
        Index("ix_work_orders_status", "status"),
        Index("ix_work_orders_priority", "priority"),
        Index("ix_work_orders_opened_at", "opened_at"),
        Index("ix_work_orders_scheduled_at", "scheduled_at"),
        Index("ix_work_orders_completed_at", "completed_at"),
    )

    work_order_number: Mapped[str] = mapped_column(String(120), nullable=False)
    equipment_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("equipment.id", ondelete="RESTRICT"),
        nullable=False,
    )
    component_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("components.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    priority: Mapped[str] = mapped_column(
        String(40), nullable=False, default=WorkOrderPriority.UNKNOWN.value
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=WorkOrderStatus.UNKNOWN.value
    )
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closure_notes: Mapped[str | None] = mapped_column(nullable=True)

    @validates("opened_at", "completed_at")
    def validate_time_order(self, key: str, value: datetime | None) -> datetime | None:
        opened_at = value if key == "opened_at" else self.opened_at
        completed_at = value if key == "completed_at" else self.completed_at
        if opened_at is not None and completed_at is not None and completed_at < opened_at:
            raise ValueError("completed_at cannot be before opened_at")
        return value
