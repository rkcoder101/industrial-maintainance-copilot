from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.constraints import enum_check
from app.models.enums import ParseStatus


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(enum_check("parse_status", ParseStatus), name="ck_documents_parse_status"),
        CheckConstraint(
            "file_size_bytes is null or file_size_bytes >= 0", name="ck_documents_size"
        ),
        CheckConstraint("page_count is null or page_count >= 0", name="ck_documents_page_count"),
        Index("ix_documents_document_code", "document_code", unique=True),
        Index("ix_documents_sha256", "sha256", unique=True),
        Index("ix_documents_parse_status", "parse_status"),
    )

    document_code: Mapped[str] = mapped_column(String(120), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parse_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=ParseStatus.REGISTERED.value,
    )
    parse_warnings_json: Mapped[list[Any]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DocumentPage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_pages_document_page"),
        CheckConstraint("page_number > 0", name="ck_document_pages_page_positive"),
        CheckConstraint("width is null or width > 0", name="ck_document_pages_width_positive"),
        CheckConstraint("height is null or height > 0", name="ck_document_pages_height_positive"),
        Index("ix_document_pages_document_id", "document_id"),
    )

    document_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(nullable=False)
    text_content: Mapped[str | None] = mapped_column(nullable=True)
    rendered_image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    width: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    document: Mapped[Document] = relationship(back_populates="pages")


class Chunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_index"),
        CheckConstraint("token_count is null or token_count >= 0", name="ck_chunks_token_count"),
        Index("ix_chunks_document_id", "document_id"),
        Index("ix_chunks_document_page_id", "document_page_id"),
        Index("ix_chunks_equipment_id", "equipment_id"),
        Index("ix_chunks_chunk_kind", "chunk_kind"),
    )

    document_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_page_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    equipment_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("equipment.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    chunk_kind: Mapped[str | None] = mapped_column(String(80), nullable=True)
    section_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    text_content: Mapped[str | None] = mapped_column(nullable=True)
    token_count: Mapped[int | None] = mapped_column(nullable=True)
    citation_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bounding_box_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    parser_metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    document: Mapped[Document] = relationship(back_populates="chunks")


class Citation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "citations"
    __table_args__ = (
        Index("ix_citations_document_id", "document_id"),
        Index("ix_citations_document_page_id", "document_page_id"),
        Index("ix_citations_chunk_id", "chunk_id"),
    )

    document_id: Mapped[Any] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_page_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_id: Mapped[Any | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    evidence_excerpt: Mapped[str | None] = mapped_column(nullable=True)
    bounding_box_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
