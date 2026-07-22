from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

FactTypeLiteral = Literal[
    "equipment_mention",
    "event",
    "failure_event",
    "measurement",
    "maintenance_action",
    "work_order",
    "procedure",
    "compliance_candidate",
    "relationship",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractionCandidate(StrictModel):
    equipment_tags: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    eligible: bool = True
    reason: str | None = None


class ExtractionRequest(StrictModel):
    document_id: UUID
    document_code: str
    chunk_id: UUID
    chunk_index: int
    citation_label: str | None = None
    first_page_number: int | None = None
    last_page_number: int | None = None
    section_path: str | None = None
    text: str
    candidates: ExtractionCandidate
    prompt_version: str


class Evidence(StrictModel):
    text: str = Field(min_length=1, max_length=1200)
    page_number: int | None = Field(default=None, ge=1)


class ProviderFact(StrictModel):
    fact_type: FactTypeLiteral
    equipment_tag: str | None = Field(default=None, max_length=120)
    confidence: float = Field(ge=0, le=1)
    evidence: Evidence
    summary: str | None = Field(default=None, max_length=500)
    event_type: str | None = Field(default=None, max_length=40)
    severity: str | None = Field(default=None, max_length=40)
    status: str | None = Field(default=None, max_length=40)
    happened_at: datetime | None = None
    metric_name: str | None = Field(default=None, max_length=160)
    metric_value: Decimal | None = None
    unit: str | None = Field(default=None, max_length=40)
    action_type: str | None = Field(default=None, max_length=120)
    work_order_number: str | None = Field(default=None, max_length=120)
    procedure_code: str | None = Field(default=None, max_length=120)
    revision: str | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, max_length=255)
    failure_mode: str | None = Field(default=None, max_length=160)
    failure_mechanism: str | None = Field(default=None, max_length=160)
    symptoms: list[str] = Field(default_factory=list, max_length=20)
    description: str | None = None
    alias: str | None = Field(default=None, max_length=160)
    relationship_type: str | None = Field(default=None, max_length=120)
    target: str | None = Field(default=None, max_length=160)

    @field_validator("equipment_tag", "event_type", "severity", "status", mode="after")
    @classmethod
    def normalize_optional_token(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ProviderExtractionResponse(StrictModel):
    facts: list[ProviderFact] = Field(default_factory=list, max_length=40)
    warnings: list[str] = Field(default_factory=list, max_length=20)
