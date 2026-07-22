"""add document processing artifacts

Revision ID: a6475f41aece
Revises: 81f572ea2231
Create Date: 2026-07-22 09:53:07.780659+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a6475f41aece"
down_revision: str | None = "81f572ea2231"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_processing_runs",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("parser_name", sa.String(length=120), nullable=True),
        sa.Column("parser_version", sa.String(length=120), nullable=True),
        sa.Column("fallback_parser_name", sa.String(length=120), nullable=True),
        sa.Column("ocr_used", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("page_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("block_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("warning_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("warnings_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('registered', 'pending', 'processing', 'completed', "
            "'completed_with_warnings', 'failed')",
            name="ck_document_processing_runs_status",
        ),
        sa.CheckConstraint("block_count >= 0", name="ck_processing_runs_block_count"),
        sa.CheckConstraint("chunk_count >= 0", name="ck_processing_runs_chunk_count"),
        sa.CheckConstraint(
            "duration_ms is null or duration_ms >= 0",
            name="ck_processing_runs_duration",
        ),
        sa.CheckConstraint("page_count >= 0", name="ck_processing_runs_page_count"),
        sa.CheckConstraint("warning_count >= 0", name="ck_processing_runs_warning_count"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_processing_runs_document_id",
        "document_processing_runs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_processing_runs_started_at",
        "document_processing_runs",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        "ix_processing_runs_status",
        "document_processing_runs",
        ["status"],
        unique=False,
    )
    op.create_table(
        "document_blocks",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_page_id", sa.Uuid(), nullable=True),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(length=40), nullable=False),
        sa.Column("section_path", sa.String(length=1024), nullable=True),
        sa.Column("heading_level", sa.Integer(), nullable=True),
        sa.Column("text_content", sa.String(), nullable=True),
        sa.Column("bounding_box_json", sa.JSON(), nullable=True),
        sa.Column("table_metadata_json", sa.JSON(), nullable=True),
        sa.Column("parser_metadata_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "block_type in ('heading', 'paragraph', 'list', 'table', 'table_row', "
            "'caption', 'header', 'footer', 'form_field', 'image_text', 'unknown')",
            name="ck_document_blocks_type",
        ),
        sa.CheckConstraint(
            "heading_level is null or heading_level > 0",
            name="ck_document_blocks_heading_level",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_page_id"], ["document_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_page_id",
            "block_index",
            name="uq_document_blocks_page_index",
        ),
    )
    op.create_index(
        "ix_document_blocks_document_id",
        "document_blocks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_blocks_page_id",
        "document_blocks",
        ["document_page_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_blocks_type",
        "document_blocks",
        ["block_type"],
        unique=False,
    )
    op.add_column("chunks", sa.Column("first_page_number", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("last_page_number", sa.Integer(), nullable=True))
    op.add_column(
        "chunks",
        sa.Column("source_block_ids_json", sa.JSON(), server_default="[]", nullable=False),
    )
    op.add_column("chunks", sa.Column("equipment_hint", sa.String(length=120), nullable=True))
    op.create_check_constraint(
        "ck_chunks_first_page_positive",
        "chunks",
        "first_page_number is null or first_page_number > 0",
    )
    op.create_check_constraint(
        "ck_chunks_last_page_positive",
        "chunks",
        "last_page_number is null or last_page_number > 0",
    )
    op.add_column(
        "document_pages", sa.Column("logical_page_key", sa.String(length=160), nullable=True)
    )
    op.add_column(
        "document_pages",
        sa.Column("ocr_used", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("document_pages", sa.Column("ocr_confidence", sa.Float(), nullable=True))
    op.add_column(
        "document_pages",
        sa.Column("warnings_json", sa.JSON(), server_default="[]", nullable=False),
    )
    op.add_column(
        "document_pages",
        sa.Column("parser_metadata_json", sa.JSON(), server_default="{}", nullable=False),
    )
    op.add_column("documents", sa.Column("parser_version", sa.String(length=120), nullable=True))
    op.add_column(
        "documents", sa.Column("parsing_started_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("parsing_completed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("documents", sa.Column("processing_duration_ms", sa.Integer(), nullable=True))
    op.add_column(
        "documents", sa.Column("ocr_used", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column(
        "documents",
        sa.Column("normalized_metadata_json", sa.JSON(), server_default="{}", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("documents", "normalized_metadata_json")
    op.drop_column("documents", "ocr_used")
    op.drop_column("documents", "processing_duration_ms")
    op.drop_column("documents", "parsing_completed_at")
    op.drop_column("documents", "parsing_started_at")
    op.drop_column("documents", "parser_version")
    op.drop_column("document_pages", "parser_metadata_json")
    op.drop_column("document_pages", "warnings_json")
    op.drop_column("document_pages", "ocr_confidence")
    op.drop_column("document_pages", "ocr_used")
    op.drop_column("document_pages", "logical_page_key")
    op.drop_constraint("ck_chunks_last_page_positive", "chunks", type_="check")
    op.drop_constraint("ck_chunks_first_page_positive", "chunks", type_="check")
    op.drop_column("chunks", "equipment_hint")
    op.drop_column("chunks", "source_block_ids_json")
    op.drop_column("chunks", "last_page_number")
    op.drop_column("chunks", "first_page_number")
    op.drop_index("ix_document_blocks_type", table_name="document_blocks")
    op.drop_index("ix_document_blocks_page_id", table_name="document_blocks")
    op.drop_index("ix_document_blocks_document_id", table_name="document_blocks")
    op.drop_table("document_blocks")
    op.drop_index("ix_processing_runs_status", table_name="document_processing_runs")
    op.drop_index("ix_processing_runs_started_at", table_name="document_processing_runs")
    op.drop_index("ix_processing_runs_document_id", table_name="document_processing_runs")
    op.drop_table("document_processing_runs")
