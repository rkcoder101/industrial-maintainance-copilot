from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.documents import Document


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, document: Document) -> Document:
        self.session.add(document)
        return document

    def get_by_id(self, document_id: UUID) -> Document | None:
        return self.session.get(Document, document_id)

    def get_by_sha256(self, sha256: str) -> Document | None:
        return self.session.scalar(select(Document).where(Document.sha256 == sha256))

    def checksum_exists(self, sha256: str) -> bool:
        return self.get_by_sha256(sha256) is not None

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        file_type: str | None = None,
        source_type: str | None = None,
        parse_status: str | None = None,
        uploaded_from: datetime | None = None,
        uploaded_to: datetime | None = None,
    ) -> tuple[list[Document], int]:
        filters: list[ColumnElement[bool]] = []
        if search:
            filters.append(Document.original_filename.ilike(f"%{search}%"))
        if file_type:
            filters.append(Document.file_type == file_type)
        if source_type:
            filters.append(Document.source_type == source_type)
        if parse_status:
            filters.append(Document.parse_status == parse_status)
        if uploaded_from:
            filters.append(Document.uploaded_at >= uploaded_from)
        if uploaded_to:
            filters.append(Document.uploaded_at <= uploaded_to)

        base_query: Select[tuple[Document]] = select(Document)
        count_query = select(func.count()).select_from(Document)
        if filters:
            base_query = base_query.where(*filters)
            count_query = count_query.where(*filters)

        offset = (page - 1) * page_size
        query = (
            base_query.order_by(Document.uploaded_at.desc(), Document.id)
            .limit(page_size)
            .offset(offset)
        )
        items = list(self.session.scalars(query).all())
        total = self.session.scalar(count_query) or 0
        return items, total
