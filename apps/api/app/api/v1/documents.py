from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.documents import (
    ChunkListResponse,
    ChunkRead,
    DocumentListResponse,
    DocumentPageListItem,
    DocumentPageRead,
    DocumentProcessingRunRead,
    DocumentProcessingStatusRead,
    DocumentRead,
    ProcessingResponse,
)
from app.schemas.extraction import (
    DocumentExtractionStatusRead,
    ExtractionResponse,
    ExtractionRunRead,
)
from app.services.documents import DocumentService
from app.services.extraction import DocumentExtractionService
from app.services.processing import DocumentProcessingService

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


@router.post("/{document_id}/process", response_model=ProcessingResponse)
async def process_document(
    document_id: UUID,
    force: bool = Query(default=False),
) -> ProcessingResponse:
    with SessionLocal() as session:
        return DocumentProcessingService(session, settings=get_settings()).process_document(
            document_id,
            force=force,
        )


@router.post("/{document_id}/process/retry", response_model=ProcessingResponse)
async def retry_document_processing(
    document_id: UUID,
    force: bool = Query(default=False),
) -> ProcessingResponse:
    with SessionLocal() as session:
        return DocumentProcessingService(session, settings=get_settings()).retry_document(
            document_id,
            force=force,
        )


@router.get("/{document_id}/processing", response_model=DocumentProcessingStatusRead)
async def get_document_processing_status(document_id: UUID) -> DocumentProcessingStatusRead:
    with SessionLocal() as session:
        return DocumentProcessingService(session, settings=get_settings()).get_status(document_id)


@router.get("/{document_id}/processing/runs", response_model=list[DocumentProcessingRunRead])
async def list_document_processing_runs(document_id: UUID) -> list[DocumentProcessingRunRead]:
    with SessionLocal() as session:
        return DocumentProcessingService(session, settings=get_settings()).list_runs(document_id)


@router.get("/{document_id}/pages", response_model=list[DocumentPageListItem])
async def list_document_pages(document_id: UUID) -> list[DocumentPageListItem]:
    with SessionLocal() as session:
        return DocumentProcessingService(session, settings=get_settings()).list_pages(document_id)


@router.get("/{document_id}/pages/{page_number}", response_model=DocumentPageRead)
async def get_document_page(document_id: UUID, page_number: int) -> DocumentPageRead:
    with SessionLocal() as session:
        return DocumentProcessingService(session, settings=get_settings()).get_page(
            document_id,
            page_number,
        )


@router.get("/{document_id}/pages/{page_number}/image")
async def get_document_page_image(document_id: UUID, page_number: int) -> Response:
    with SessionLocal() as session:
        path = DocumentProcessingService(session, settings=get_settings()).get_page_image_path(
            document_id,
            page_number,
        )
    return Response(
        path.read_bytes(),
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.get("/{document_id}/chunks", response_model=ChunkListResponse)
async def list_document_chunks(
    document_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    chunk_kind: str | None = Query(default=None, max_length=80),
) -> ChunkListResponse:
    with SessionLocal() as session:
        return DocumentProcessingService(session, settings=get_settings()).list_chunks(
            document_id,
            page=page,
            page_size=page_size,
            chunk_kind=chunk_kind,
        )


@router.get("/{document_id}/chunks/{chunk_id}", response_model=ChunkRead)
async def get_document_chunk(document_id: UUID, chunk_id: UUID) -> ChunkRead:
    with SessionLocal() as session:
        return DocumentProcessingService(session, settings=get_settings()).get_chunk(
            document_id, chunk_id
        )


@router.post("/{document_id}/extract", response_model=ExtractionResponse)
async def extract_document(
    document_id: UUID,
    force: bool = Query(default=False),
) -> ExtractionResponse:
    with SessionLocal() as session:
        return DocumentExtractionService(session, settings=get_settings()).extract_document(
            document_id,
            force=force,
        )


@router.post("/{document_id}/extract/retry", response_model=ExtractionResponse)
async def retry_document_extraction(
    document_id: UUID,
    force: bool = Query(default=False),
) -> ExtractionResponse:
    with SessionLocal() as session:
        return DocumentExtractionService(session, settings=get_settings()).retry_document(
            document_id,
            force=force,
        )


@router.get("/{document_id}/extraction", response_model=DocumentExtractionStatusRead)
async def get_document_extraction_status(document_id: UUID) -> DocumentExtractionStatusRead:
    with SessionLocal() as session:
        return DocumentExtractionService(session, settings=get_settings()).get_status(document_id)


@router.get("/{document_id}/extraction/runs", response_model=list[ExtractionRunRead])
async def list_document_extraction_runs(document_id: UUID) -> list[ExtractionRunRead]:
    with SessionLocal() as session:
        return DocumentExtractionService(session, settings=get_settings()).list_runs(document_id)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: UUID) -> DocumentRead:
    with SessionLocal() as session:
        return DocumentService(session).get_document(document_id)
