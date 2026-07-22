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


class BlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    TABLE_ROW = "table_row"
    CAPTION = "caption"
    HEADER = "header"
    FOOTER = "footer"
    FORM_FIELD = "form_field"
    IMAGE_TEXT = "image_text"
    UNKNOWN = "unknown"


class ChunkKind(StrEnum):
    MANUAL_SECTION = "manual_section"
    PROCEDURE = "procedure"
    INCIDENT = "incident"
    INSPECTION = "inspection"
    MAINTENANCE_RECORD = "maintenance_record"
    CHECKLIST = "checklist"
    TABLE = "table"
    SPREADSHEET_ROWS = "spreadsheet_rows"
    GENERAL_TEXT = "general_text"
    IMAGE_OCR = "image_ocr"
    UNKNOWN = "unknown"


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


class IngestionItemStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    STORED = "stored"
    DUPLICATE = "duplicate"
    FAILED = "failed"


class ChunkExtractionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SKIPPED = "skipped"
    COMPLETED = "completed"
    FAILED = "failed"


class ExtractionFactType(StrEnum):
    EQUIPMENT_MENTION = "equipment_mention"
    EVENT = "event"
    FAILURE_EVENT = "failure_event"
    MEASUREMENT = "measurement"
    MAINTENANCE_ACTION = "maintenance_action"
    WORK_ORDER = "work_order"
    PROCEDURE = "procedure"
    COMPLIANCE_CANDIDATE = "compliance_candidate"
    RELATIONSHIP = "relationship"


class ExtractionFactStatus(StrEnum):
    STAGED = "staged"
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    ERROR = "error"
