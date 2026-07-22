from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query

from app.db.session import SessionLocal
from app.schemas.documents import DocumentListResponse, DocumentRead
from app.services.documents import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=120),
    file_type: str | None = Query(default=None, max_length=80),
    source_type: str | None = Query(default=None, max_length=120),
    parse_status: str | None = Query(default=None, max_length=40),
    uploaded_from: datetime | None = None,
    uploaded_to: datetime | None = None,
) -> DocumentListResponse:
    with SessionLocal() as session:
        return DocumentService(session).list_documents(
            page=page,
            page_size=page_size,
            search=search,
            file_type=file_type,
            source_type=source_type,
            parse_status=parse_status,
            uploaded_from=uploaded_from,
            uploaded_to=uploaded_to,
        )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: UUID) -> DocumentRead:
    with SessionLocal() as session:
        return DocumentService(session).get_document(document_id)
