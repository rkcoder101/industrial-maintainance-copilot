from typing import Any

from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base, ProvenanceMixin, TimestampMixin, UUIDPrimaryKeyMixin


class GraphEdge(UUIDPrimaryKeyMixin, ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "graph_edges"
    __table_args__ = (
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_graph_edges_confidence",
        ),
        Index("ix_graph_edges_source", "source_type", "source_id"),
        Index("ix_graph_edges_target", "target_type", "target_id"),
        Index("ix_graph_edges_relationship_type", "relationship_type"),
    )

    source_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_id: Mapped[Any] = mapped_column(Uuid(as_uuid=True), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(120), nullable=False)
    target_id: Mapped[Any] = mapped_column(Uuid(as_uuid=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )
