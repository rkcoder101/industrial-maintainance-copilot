"""add structured extraction artifacts

Revision ID: 3642e86566a9
Revises: a6475f41aece
Create Date: 2026-07-22 10:55:12.966169+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3642e86566a9"
down_revision: str | None = "a6475f41aece"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chunk_extraction_runs",
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("provider_name", sa.String(length=120), nullable=True),
        sa.Column("model_name", sa.String(length=160), nullable=True),
        sa.Column("prompt_version", sa.String(length=120), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("candidate_summary_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("input_excerpt", sa.String(), nullable=True),
        sa.Column("response_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("validation_errors_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("warnings_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("fact_count", sa.Integer(), nullable=False),
        sa.Column("accepted_fact_count", sa.Integer(), nullable=False),
        sa.Column("rejected_fact_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_fact_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
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
            "status in ('pending', 'processing', 'skipped', 'completed', 'failed')",
            name="ck_chunk_extraction_runs_status",
        ),
        sa.CheckConstraint("accepted_fact_count >= 0", name="ck_chunk_extraction_runs_accepted"),
        sa.CheckConstraint("duplicate_fact_count >= 0", name="ck_chunk_extraction_runs_duplicate"),
        sa.CheckConstraint(
            "duration_ms is null or duration_ms >= 0",
            name="ck_chunk_extraction_runs_duration",
        ),
        sa.CheckConstraint("fact_count >= 0", name="ck_chunk_extraction_runs_fact_count"),
        sa.CheckConstraint("rejected_fact_count >= 0", name="ck_chunk_extraction_runs_rejected"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extraction_run_id"], ["extraction_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chunk_extraction_runs_chunk_id",
        "chunk_extraction_runs",
        ["chunk_id"],
        unique=False,
    )
    op.create_index(
        "ix_chunk_extraction_runs_document_id",
        "chunk_extraction_runs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_chunk_extraction_runs_run_id",
        "chunk_extraction_runs",
        ["extraction_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_chunk_extraction_runs_status",
        "chunk_extraction_runs",
        ["status"],
        unique=False,
    )
    op.create_table(
        "equipment_aliases",
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(length=160), nullable=False),
        sa.Column("alias_type", sa.String(length=80), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("source_page_id", sa.Uuid(), nullable=True),
        sa.Column("source_chunk_id", sa.Uuid(), nullable=True),
        sa.Column("evidence_span", sa.String(), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("extractor_version", sa.String(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False),
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
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_equipment_aliases_confidence",
        ),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_page_id"], ["document_pages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("equipment_id", "alias", name="uq_equipment_aliases_equipment_alias"),
    )
    op.create_index("ix_equipment_aliases_alias", "equipment_aliases", ["alias"], unique=False)
    op.create_index(
        "ix_equipment_aliases_equipment_id",
        "equipment_aliases",
        ["equipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_equipment_aliases_source_chunk_id",
        "equipment_aliases",
        ["source_chunk_id"],
        unique=False,
    )
    op.create_table(
        "extracted_facts",
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_extraction_run_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("source_page_id", sa.Uuid(), nullable=True),
        sa.Column("source_chunk_id", sa.Uuid(), nullable=True),
        sa.Column("equipment_id", sa.Uuid(), nullable=True),
        sa.Column("fact_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("evidence_span", sa.String(), nullable=True),
        sa.Column("source_text", sa.String(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("normalized_payload_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("validation_errors_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("warnings_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("canonical_type", sa.String(length=120), nullable=True),
        sa.Column("canonical_id", sa.Uuid(), nullable=True),
        sa.Column("extractor_version", sa.String(length=120), nullable=True),
        sa.Column("prompt_version", sa.String(length=120), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
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
            "fact_type in ('equipment_mention', 'event', 'failure_event', 'measurement', "
            "'maintenance_action', 'work_order', 'procedure', 'compliance_candidate', "
            "'relationship')",
            name="ck_extracted_facts_type",
        ),
        sa.CheckConstraint(
            "status in ('staged', 'accepted', 'duplicate', 'rejected', 'error')",
            name="ck_extracted_facts_status",
        ),
        sa.CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_extracted_facts_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_extraction_run_id"], ["chunk_extraction_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["extraction_run_id"], ["extraction_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_page_id"], ["document_pages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extracted_facts_canonical",
        "extracted_facts",
        ["canonical_type", "canonical_id"],
        unique=False,
    )
    op.create_index(
        "ix_extracted_facts_chunk_id",
        "extracted_facts",
        ["source_chunk_id"],
        unique=False,
    )
    op.create_index(
        "ix_extracted_facts_document_id",
        "extracted_facts",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_extracted_facts_equipment_id",
        "extracted_facts",
        ["equipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_extracted_facts_fingerprint",
        "extracted_facts",
        ["fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_extracted_facts_run_id", "extracted_facts", ["extraction_run_id"], unique=False
    )
    op.create_index("ix_extracted_facts_status", "extracted_facts", ["status"], unique=False)
    op.create_index("ix_extracted_facts_type", "extracted_facts", ["fact_type"], unique=False)

    op.add_column("extraction_runs", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column(
        "extraction_runs",
        sa.Column("force", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    for column_name in (
        "total_chunk_count",
        "eligible_chunk_count",
        "processed_chunk_count",
        "skipped_chunk_count",
        "failed_chunk_count",
        "fact_count",
        "accepted_fact_count",
        "rejected_fact_count",
        "duplicate_fact_count",
        "warning_count",
    ):
        op.add_column(
            "extraction_runs",
            sa.Column(column_name, sa.Integer(), server_default="0", nullable=False),
        )
        op.alter_column("extraction_runs", column_name, server_default=None)
    op.add_column("extraction_runs", sa.Column("error_code", sa.String(length=120), nullable=True))
    op.add_column(
        "extraction_runs",
        sa.Column("warnings_json", sa.JSON(), server_default="[]", nullable=False),
    )
    op.alter_column("extraction_runs", "force", server_default=None)
    op.create_check_constraint(
        "ck_extraction_runs_duration",
        "extraction_runs",
        "duration_ms is null or duration_ms >= 0",
    )
    for constraint_name, column_name in (
        ("ck_extraction_runs_total_chunks", "total_chunk_count"),
        ("ck_extraction_runs_eligible_chunks", "eligible_chunk_count"),
        ("ck_extraction_runs_processed_chunks", "processed_chunk_count"),
        ("ck_extraction_runs_skipped_chunks", "skipped_chunk_count"),
        ("ck_extraction_runs_failed_chunks", "failed_chunk_count"),
        ("ck_extraction_runs_fact_count", "fact_count"),
        ("ck_extraction_runs_accepted_count", "accepted_fact_count"),
        ("ck_extraction_runs_rejected_count", "rejected_fact_count"),
        ("ck_extraction_runs_duplicate_count", "duplicate_fact_count"),
        ("ck_extraction_runs_warning_count", "warning_count"),
    ):
        op.create_check_constraint(constraint_name, "extraction_runs", f"{column_name} >= 0")


def downgrade() -> None:
    for constraint_name in (
        "ck_extraction_runs_duplicate_count",
        "ck_extraction_runs_warning_count",
        "ck_extraction_runs_rejected_count",
        "ck_extraction_runs_accepted_count",
        "ck_extraction_runs_fact_count",
        "ck_extraction_runs_failed_chunks",
        "ck_extraction_runs_skipped_chunks",
        "ck_extraction_runs_processed_chunks",
        "ck_extraction_runs_eligible_chunks",
        "ck_extraction_runs_total_chunks",
        "ck_extraction_runs_duration",
    ):
        op.drop_constraint(constraint_name, "extraction_runs", type_="check")
    op.drop_column("extraction_runs", "warnings_json")
    op.drop_column("extraction_runs", "error_code")
    op.drop_column("extraction_runs", "warning_count")
    op.drop_column("extraction_runs", "duplicate_fact_count")
    op.drop_column("extraction_runs", "rejected_fact_count")
    op.drop_column("extraction_runs", "accepted_fact_count")
    op.drop_column("extraction_runs", "fact_count")
    op.drop_column("extraction_runs", "failed_chunk_count")
    op.drop_column("extraction_runs", "skipped_chunk_count")
    op.drop_column("extraction_runs", "processed_chunk_count")
    op.drop_column("extraction_runs", "eligible_chunk_count")
    op.drop_column("extraction_runs", "total_chunk_count")
    op.drop_column("extraction_runs", "force")
    op.drop_column("extraction_runs", "duration_ms")
    op.drop_index("ix_extracted_facts_type", table_name="extracted_facts")
    op.drop_index("ix_extracted_facts_status", table_name="extracted_facts")
    op.drop_index("ix_extracted_facts_run_id", table_name="extracted_facts")
    op.drop_index("ix_extracted_facts_fingerprint", table_name="extracted_facts")
    op.drop_index("ix_extracted_facts_equipment_id", table_name="extracted_facts")
    op.drop_index("ix_extracted_facts_document_id", table_name="extracted_facts")
    op.drop_index("ix_extracted_facts_chunk_id", table_name="extracted_facts")
    op.drop_index("ix_extracted_facts_canonical", table_name="extracted_facts")
    op.drop_table("extracted_facts")
    op.drop_index("ix_equipment_aliases_source_chunk_id", table_name="equipment_aliases")
    op.drop_index("ix_equipment_aliases_equipment_id", table_name="equipment_aliases")
    op.drop_index("ix_equipment_aliases_alias", table_name="equipment_aliases")
    op.drop_table("equipment_aliases")
    op.drop_index("ix_chunk_extraction_runs_status", table_name="chunk_extraction_runs")
    op.drop_index("ix_chunk_extraction_runs_run_id", table_name="chunk_extraction_runs")
    op.drop_index("ix_chunk_extraction_runs_document_id", table_name="chunk_extraction_runs")
    op.drop_index("ix_chunk_extraction_runs_chunk_id", table_name="chunk_extraction_runs")
    op.drop_table("chunk_extraction_runs")
