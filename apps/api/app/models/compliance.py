from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base, MetadataMixin, ProvenanceMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.constraints import enum_check
from app.models.enums import ComplianceRuleType, Criticality, FindingStatus, Severity


class ComplianceRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "compliance_rules"
    __table_args__ = (
        UniqueConstraint("rule_code", name="uq_compliance_rules_code"),
        CheckConstraint(
            enum_check("applicable_criticality", Criticality)
            + " or applicable_criticality is null",
            name="ck_compliance_rules_criticality",
        ),
        CheckConstraint(
            enum_check("rule_type", ComplianceRuleType), name="ck_compliance_rules_type"
        ),
        CheckConstraint(enum_check("severity", Severity), name="ck_compliance_rules_severity"),
        Index("ix_compliance_rules_enabled", "enabled"),
        Index("ix_compliance_rules_type", "rule_type"),
    )

    rule_code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    applicable_equipment_class: Mapped[str | None] = mapped_column(String(120), nullable=True)
    applicable_criticality: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(80), nullable=False)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(40), nullable=False, default=Severity.UNKNOWN.value
    )
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)


class ComplianceFinding(UUIDPrimaryKeyMixin, ProvenanceMixin, MetadataMixin, TimestampMixin, Base):
    __tablename__ = "compliance_findings"
    __table_args__ = (
        UniqueConstraint("finding_code", name="uq_compliance_findings_code"),
        CheckConstraint(enum_check("status", FindingStatus), name="ck_compliance_findings_status"),
        CheckConstraint(enum_check("severity", Severity), name="ck_compliance_findings_severity"),
        CheckConstraint(
            "resolved_at is null or detected_at is null or resolved_at >= detected_at",
            name="ck_compliance_findings_time_order",
        ),
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_compliance_findings_confidence",
        ),
        Index("ix_compliance_findings_rule_id", "rule_id"),
        Index("ix_compliance_findings_equipment_id", "equipment_id"),
        Index("ix_compliance_findings_status", "status"),
        Index("ix_compliance_findings_severity", "severity"),
        Index("ix_compliance_findings_detected_at", "detected_at"),
    )

    finding_code: Mapped[str] = mapped_column(String(120), nullable=False)
    rule_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("compliance_rules.id", ondelete="RESTRICT"),
        nullable=False,
    )
    equipment_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("equipment.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=FindingStatus.OPEN.value
    )
    severity: Mapped[str] = mapped_column(
        String(40), nullable=False, default=Severity.UNKNOWN.value
    )
    reason: Mapped[str] = mapped_column(nullable=False)
    expected_evidence: Mapped[str | None] = mapped_column(nullable=True)
    available_evidence: Mapped[str | None] = mapped_column(nullable=True)
    missing_evidence: Mapped[str | None] = mapped_column(nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(nullable=True)

    @validates("detected_at", "resolved_at")
    def validate_time_order(self, key: str, value: datetime | None) -> datetime | None:
        detected_at = value if key == "detected_at" else self.detected_at
        resolved_at = value if key == "resolved_at" else self.resolved_at
        if detected_at is not None and resolved_at is not None and resolved_at < detected_at:
            raise ValueError("resolved_at cannot be before detected_at")
        return value
