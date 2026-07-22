from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.constraints import enum_check
from app.models.enums import (
    ChunkExtractionStatus,
    ExtractionFactStatus,
    ExtractionFactType,
    IngestionItemStatus,
    JobStatus,
)


class IngestionJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint(enum_check("status", JobStatus), name="ck_ingestion_jobs_status"),
        CheckConstraint("total_files >= 0", name="ck_ingestion_jobs_total_files"),
        CheckConstraint("processed_files >= 0", name="ck_ingestion_jobs_processed_files"),
        CheckConstraint("failed_files >= 0", name="ck_ingestion_jobs_failed_files"),
        CheckConstraint(
            "processed_files + failed_files <= total_files",
            name="ck_ingestion_jobs_count_bounds",
        ),
        Index("ix_ingestion_jobs_status", "status"),
        Index("ix_ingestion_jobs_started_at", "started_at"),
    )

    status: Mapped[str] = mapped_column(String(40), nullable=False, default=JobStatus.PENDING.value)
    total_files: Mapped[int] = mapped_column(default=0, nullable=False)
    processed_files: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_files: Mapped[int] = mapped_column(default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    items: Mapped[list["IngestionItem"]] = relationship(
        back_populates="ingestion_job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @validates("total_files", "processed_files", "failed_files")
    def validate_counts(self, key: str, value: int) -> int:
        total_files = value if key == "total_files" else (self.total_files or 0)
        processed_files = value if key == "processed_files" else (self.processed_files or 0)
        failed_files = value if key == "failed_files" else (self.failed_files or 0)
        if value < 0:
            raise ValueError("job file counts cannot be negative")
        if processed_files + failed_files > total_files:
            raise ValueError("processed_files plus failed_files cannot exceed total_files")
        return value


class IngestionItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_items"
    __table_args__ = (
        CheckConstraint(
            enum_check("status", IngestionItemStatus),
            name="ck_ingestion_items_status",
        ),
        CheckConstraint(
            "actual_size_bytes is null or actual_size_bytes >= 0", name="ck_ingestion_items_size"
        ),
        CheckConstraint("attempt_count >= 0", name="ck_ingestion_items_attempt_count"),
        Index("ix_ingestion_items_job_id", "ingestion_job_id"),
        Index("ix_ingestion_items_document_id", "document_id"),
        Index("ix_ingestion_items_status", "status"),
        Index("ix_ingestion_items_sha256", "sha256"),
    )

    ingestion_job_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ingestion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    duplicate_of_document_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=IngestionItemStatus.PENDING.value,
    )
    detected_file_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    detected_mime_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    actual_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scanner_status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scanner_message: Mapped[str | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    ingestion_job: Mapped[IngestionJob] = relationship(back_populates="items")

    @validates("attempt_count")
    def validate_attempt_count(self, _: str, value: int) -> int:
        if value < 0:
            raise ValueError("attempt_count cannot be negative")
        return value

    @validates("actual_size_bytes")
    def validate_actual_size(self, _: str, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("actual_size_bytes cannot be negative")
        return value


class ExtractionRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "extraction_runs"
    __table_args__ = (
        CheckConstraint(enum_check("status", JobStatus), name="ck_extraction_runs_status"),
        CheckConstraint(
            "duration_ms is null or duration_ms >= 0",
            name="ck_extraction_runs_duration",
        ),
        CheckConstraint("total_chunk_count >= 0", name="ck_extraction_runs_total_chunks"),
        CheckConstraint("eligible_chunk_count >= 0", name="ck_extraction_runs_eligible_chunks"),
        CheckConstraint("processed_chunk_count >= 0", name="ck_extraction_runs_processed_chunks"),
        CheckConstraint("skipped_chunk_count >= 0", name="ck_extraction_runs_skipped_chunks"),
        CheckConstraint("failed_chunk_count >= 0", name="ck_extraction_runs_failed_chunks"),
        CheckConstraint("fact_count >= 0", name="ck_extraction_runs_fact_count"),
        CheckConstraint("accepted_fact_count >= 0", name="ck_extraction_runs_accepted_count"),
        CheckConstraint("rejected_fact_count >= 0", name="ck_extraction_runs_rejected_count"),
        CheckConstraint("duplicate_fact_count >= 0", name="ck_extraction_runs_duplicate_count"),
        CheckConstraint("warning_count >= 0", name="ck_extraction_runs_warning_count"),
        Index("ix_extraction_runs_document_id", "document_id"),
        Index("ix_extraction_runs_status", "status"),
        Index("ix_extraction_runs_extractor", "extractor_name", "extractor_version"),
    )

    document_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=JobStatus.PENDING.value)
    extractor_name: Mapped[str] = mapped_column(String(160), nullable=False)
    extractor_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    force: Mapped[bool] = mapped_column(default=False, nullable=False)
    total_chunk_count: Mapped[int] = mapped_column(default=0, nullable=False)
    eligible_chunk_count: Mapped[int] = mapped_column(default=0, nullable=False)
    processed_chunk_count: Mapped[int] = mapped_column(default=0, nullable=False)
    skipped_chunk_count: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_chunk_count: Mapped[int] = mapped_column(default=0, nullable=False)
    fact_count: Mapped[int] = mapped_column(default=0, nullable=False)
    accepted_fact_count: Mapped[int] = mapped_column(default=0, nullable=False)
    rejected_fact_count: Mapped[int] = mapped_column(default=0, nullable=False)
    duplicate_fact_count: Mapped[int] = mapped_column(default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    warnings_json: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    chunk_runs: Mapped[list["ChunkExtractionRun"]] = relationship(
        back_populates="extraction_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    facts: Mapped[list["ExtractedFact"]] = relationship(
        back_populates="extraction_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ChunkExtractionRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chunk_extraction_runs"
    __table_args__ = (
        CheckConstraint(
            enum_check("status", ChunkExtractionStatus),
            name="ck_chunk_extraction_runs_status",
        ),
        CheckConstraint(
            "duration_ms is null or duration_ms >= 0",
            name="ck_chunk_extraction_runs_duration",
        ),
        CheckConstraint("fact_count >= 0", name="ck_chunk_extraction_runs_fact_count"),
        CheckConstraint("accepted_fact_count >= 0", name="ck_chunk_extraction_runs_accepted"),
        CheckConstraint("rejected_fact_count >= 0", name="ck_chunk_extraction_runs_rejected"),
        CheckConstraint("duplicate_fact_count >= 0", name="ck_chunk_extraction_runs_duplicate"),
        Index("ix_chunk_extraction_runs_run_id", "extraction_run_id"),
        Index("ix_chunk_extraction_runs_document_id", "document_id"),
        Index("ix_chunk_extraction_runs_chunk_id", "chunk_id"),
        Index("ix_chunk_extraction_runs_status", "status"),
    )

    extraction_run_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=ChunkExtractionStatus.PENDING.value,
    )
    provider_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    candidate_summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )
    input_excerpt: Mapped[str | None] = mapped_column(nullable=True)
    response_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )
    validation_errors_json: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
    warnings_json: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
    fact_count: Mapped[int] = mapped_column(default=0, nullable=False)
    accepted_fact_count: Mapped[int] = mapped_column(default=0, nullable=False)
    rejected_fact_count: Mapped[int] = mapped_column(default=0, nullable=False)
    duplicate_fact_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    extraction_run: Mapped[ExtractionRun] = relationship(back_populates="chunk_runs")
    facts: Mapped[list["ExtractedFact"]] = relationship(
        back_populates="chunk_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ExtractedFact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "extracted_facts"
    __table_args__ = (
        CheckConstraint(
            enum_check("fact_type", ExtractionFactType), name="ck_extracted_facts_type"
        ),
        CheckConstraint(
            enum_check("status", ExtractionFactStatus),
            name="ck_extracted_facts_status",
        ),
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_extracted_facts_confidence",
        ),
        Index("ix_extracted_facts_run_id", "extraction_run_id"),
        Index("ix_extracted_facts_document_id", "document_id"),
        Index("ix_extracted_facts_chunk_id", "source_chunk_id"),
        Index("ix_extracted_facts_equipment_id", "equipment_id"),
        Index("ix_extracted_facts_fingerprint", "fingerprint"),
        Index("ix_extracted_facts_status", "status"),
        Index("ix_extracted_facts_type", "fact_type"),
        Index("ix_extracted_facts_canonical", "canonical_type", "canonical_id"),
    )

    extraction_run_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_extraction_run_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chunk_extraction_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_page_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_chunk_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    equipment_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("equipment.id", ondelete="SET NULL"),
        nullable=True,
    )
    fact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    evidence_span: Mapped[str | None] = mapped_column(nullable=True)
    source_text: Mapped[str | None] = mapped_column(nullable=True)
    raw_payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )
    normalized_payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )
    validation_errors_json: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
    warnings_json: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(nullable=True)
    canonical_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    canonical_id: Mapped[Any | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    extractor_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    extraction_run: Mapped[ExtractionRun] = relationship(back_populates="facts")
    chunk_run: Mapped[ChunkExtractionRun | None] = relationship(back_populates="facts")
