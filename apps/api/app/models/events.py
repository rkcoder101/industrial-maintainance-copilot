from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base, MetadataMixin, ProvenanceMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.constraints import enum_check
from app.models.enums import EventStatus, EventType, MeasurementQuality, Severity


class Event(UUIDPrimaryKeyMixin, ProvenanceMixin, MetadataMixin, TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("event_code", name="uq_events_event_code"),
        CheckConstraint(enum_check("event_type", EventType), name="ck_events_event_type"),
        CheckConstraint(enum_check("severity", Severity), name="ck_events_severity"),
        CheckConstraint(enum_check("status", EventStatus), name="ck_events_status"),
        CheckConstraint(
            "end_time is null or event_time is null or end_time >= event_time",
            name="ck_events_time_order",
        ),
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_events_confidence",
        ),
        Index("ix_events_equipment_time", "equipment_id", "event_time"),
        Index("ix_events_event_type", "event_type"),
        Index("ix_events_component_id", "component_id"),
    )

    event_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
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
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    severity: Mapped[str] = mapped_column(
        String(40), nullable=False, default=Severity.UNKNOWN.value
    )
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=EventStatus.UNKNOWN.value
    )

    failure_detail: Mapped["FailureEvent | None"] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )

    @validates("event_time", "end_time")
    def validate_time_order(self, key: str, value: datetime | None) -> datetime | None:
        event_time = value if key == "event_time" else self.event_time
        end_time = value if key == "end_time" else self.end_time
        if event_time is not None and end_time is not None and end_time < event_time:
            raise ValueError("end_time cannot be before event_time")
        return value


class FailureEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "failure_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_failure_events_event_id"),
        CheckConstraint(
            "downtime_minutes is null or downtime_minutes >= 0", name="ck_failure_events_downtime"
        ),
    )

    event_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    failure_mode: Mapped[str] = mapped_column(String(160), nullable=False)
    failure_mechanism: Mapped[str | None] = mapped_column(String(160), nullable=True)
    symptoms_json: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
    detected_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    downtime_minutes: Mapped[int | None] = mapped_column(nullable=True)
    production_loss: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolution_summary: Mapped[str | None] = mapped_column(nullable=True)

    event: Mapped[Event] = relationship(back_populates="failure_detail")

    @validates("event")
    def validate_failure_event_type(self, _: str, value: Event) -> Event:
        if value.event_type != EventType.FAILURE.value:
            raise ValueError("FailureEvent can only be associated with an Event of type failure")
        return value


class Measurement(UUIDPrimaryKeyMixin, ProvenanceMixin, MetadataMixin, TimestampMixin, Base):
    __tablename__ = "measurements"
    __table_args__ = (
        CheckConstraint(enum_check("quality", MeasurementQuality), name="ck_measurements_quality"),
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_measurements_confidence",
        ),
        Index(
            "ix_measurements_equipment_metric_time", "equipment_id", "metric_name", "measured_at"
        ),
        Index("ix_measurements_component_id", "component_id"),
        Index("ix_measurements_event_id", "event_id"),
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
    event_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    metric_name: Mapped[str] = mapped_column(String(160), nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quality: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=MeasurementQuality.UNKNOWN.value,
    )
