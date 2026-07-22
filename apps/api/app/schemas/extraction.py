from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExtractionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID | None
    status: str
    extractor_name: str
    extractor_version: str | None
    model_provider: str | None
    model_name: str | None
    prompt_version: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    force: bool
    total_chunk_count: int
    eligible_chunk_count: int
    processed_chunk_count: int
    skipped_chunk_count: int
    failed_chunk_count: int
    fact_count: int
    accepted_fact_count: int
    rejected_fact_count: int
    duplicate_fact_count: int
    warning_count: int
    error_code: str | None
    error_message: str | None
    warnings_json: list[Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ChunkExtractionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    extraction_run_id: UUID
    document_id: UUID
    chunk_id: UUID | None
    status: str
    provider_name: str | None
    model_name: str | None
    prompt_version: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    candidate_summary_json: dict[str, Any]
    validation_errors_json: list[Any]
    warnings_json: list[Any]
    fact_count: int
    accepted_fact_count: int
    rejected_fact_count: int
    duplicate_fact_count: int
    error_code: str | None
    error_message: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ExtractedFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    extraction_run_id: UUID
    chunk_extraction_run_id: UUID | None
    document_id: UUID
    source_page_id: UUID | None
    source_chunk_id: UUID | None
    equipment_id: UUID | None
    fact_type: str
    status: str
    fingerprint: str
    confidence: float | None
    evidence_span: str | None
    source_text: str | None
    normalized_payload_json: dict[str, Any]
    validation_errors_json: list[Any]
    warnings_json: list[Any]
    rejection_reason: str | None
    canonical_type: str | None
    canonical_id: UUID | None
    extractor_version: str | None
    prompt_version: str | None
    accepted_at: datetime | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ExtractedFactListResponse(BaseModel):
    items: list[ExtractedFactRead]
    total: int
    page: int
    page_size: int


class DocumentExtractionStatusRead(BaseModel):
    document_id: UUID
    latest_run: ExtractionRunRead | None
    total_runs: int
    fact_count: int = Field(ge=0)
    accepted_fact_count: int = Field(ge=0)


class ExtractionResponse(BaseModel):
    status: DocumentExtractionStatusRead
