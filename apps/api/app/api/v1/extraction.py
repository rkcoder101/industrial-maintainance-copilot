from uuid import UUID

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.extraction import ExtractedFactListResponse, ExtractedFactRead, ExtractionRunRead
from app.services.extraction import DocumentExtractionService

router = APIRouter(prefix="/extraction", tags=["extraction"])


@router.get("/runs/{run_id}", response_model=ExtractionRunRead)
async def get_extraction_run(run_id: UUID) -> ExtractionRunRead:
    with SessionLocal() as session:
        return DocumentExtractionService(session, settings=get_settings()).get_run(run_id)


@router.get("/runs/{run_id}/facts", response_model=ExtractedFactListResponse)
async def list_extraction_run_facts(
    run_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None, max_length=40),
    fact_type: str | None = Query(default=None, max_length=80),
) -> ExtractedFactListResponse:
    with SessionLocal() as session:
        return DocumentExtractionService(session, settings=get_settings()).list_facts_for_run(
            run_id,
            page=page,
            page_size=page_size,
            status=status,
            fact_type=fact_type,
        )


@router.get("/facts/{fact_id}", response_model=ExtractedFactRead)
async def get_extracted_fact(fact_id: UUID) -> ExtractedFactRead:
    with SessionLocal() as session:
        return DocumentExtractionService(session, settings=get_settings()).get_fact(fact_id)
