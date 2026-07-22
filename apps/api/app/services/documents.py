from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentListResponse, DocumentRead
from app.services.ingestion_errors import DocumentNotFoundError


class DocumentService:
    def __init__(self, session: Session) -> None:
        self.repository = DocumentRepository(session)

    def list_documents(
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
    ) -> DocumentListResponse:
        items, total = self.repository.list(
            page=page,
            page_size=page_size,
            search=search,
            file_type=file_type,
            source_type=source_type,
            parse_status=parse_status,
            uploaded_from=uploaded_from,
            uploaded_to=uploaded_to,
        )
        return DocumentListResponse(
            items=[DocumentRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_document(self, document_id: UUID) -> DocumentRead:
        document = self.repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        return DocumentRead.model_validate(document)
