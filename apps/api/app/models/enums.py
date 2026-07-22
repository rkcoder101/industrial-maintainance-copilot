from enum import StrEnum


class Criticality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SAFETY_CRITICAL = "safety_critical"


class OperationalStatus(StrEnum):
    ACTIVE = "active"
    STANDBY = "standby"
    UNDER_MAINTENANCE = "under_maintenance"
    OUT_OF_SERVICE = "out_of_service"
    RETIRED = "retired"
    UNKNOWN = "unknown"


class ParseStatus(StrEnum):
    REGISTERED = "registered"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class EventType(StrEnum):
    FAILURE = "failure"
    INSPECTION = "inspection"
    MAINTENANCE = "maintenance"
    CALIBRATION = "calibration"
    MEASUREMENT = "measurement"
    OPERATIONAL = "operational"
    PROCEDURE_REVISION = "procedure_revision"
    COMPLIANCE = "compliance"
    OTHER = "other"


class Severity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class EventStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class MeasurementQuality(StrEnum):
    GOOD = "good"
    SUSPECT = "suspect"
    BAD = "bad"
    UNKNOWN = "unknown"


class ProcedureStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class ActionStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class WorkOrderPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class WorkOrderStatus(StrEnum):
    OPEN = "open"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class ComplianceRuleType(StrEnum):
    DOCUMENT_REQUIRED = "document_required"
    INSPECTION_INTERVAL = "inspection_interval"
    RCA_REQUIRED = "rca_required"
    CUSTOM = "custom"


class FindingStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class JobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
