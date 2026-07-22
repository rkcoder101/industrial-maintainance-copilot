from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import IngestionItemStatus, JobStatus


class IngestionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ingestion_job_id: UUID
    document_id: UUID | None
    duplicate_of_document_id: UUID | None
    original_filename: str
    status: IngestionItemStatus
    detected_file_type: str | None
    detected_mime_type: str | None
    actual_size_bytes: int | None
    sha256: str | None
    attempt_count: int
    error_code: str | None
    error_message: str | None
    scanner_status: str | None
    scanner_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class IngestionJobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: JobStatus
    total_files: int
    processed_files: int
    failed_files: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IngestionJobRead(IngestionJobSummary):
    items: list[IngestionItemRead]


class IngestionUploadResponse(BaseModel):
    job: IngestionJobSummary
    items: list[IngestionItemRead]


class IngestionRetryResponse(BaseModel):
    job: IngestionJobSummary
    retried_items: list[IngestionItemRead]
    message: str
