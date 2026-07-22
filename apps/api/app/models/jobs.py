from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.constraints import enum_check
from app.models.enums import IngestionItemStatus, JobStatus


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
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )
