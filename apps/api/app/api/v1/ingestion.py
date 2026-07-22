from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.ingestion import IngestionJobRead, IngestionRetryResponse, IngestionUploadResponse
from app.services.ingestion import DocumentIngestionService

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post(
    "/documents",
    response_model=IngestionUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_documents(
    response: Response,
    files: Annotated[list[UploadFile] | None, File()] = None,
    source_type: Annotated[str | None, Form(max_length=120)] = None,
) -> IngestionUploadResponse:
    with SessionLocal() as session:
        result = await DocumentIngestionService(session, settings=get_settings()).upload_documents(
            files=files,
            source_type=source_type,
        )
    if result.job.status in {"completed", "completed_with_errors", "failed"}:
        response.status_code = status.HTTP_202_ACCEPTED
    return result


@router.get("/jobs/{job_id}", response_model=IngestionJobRead)
async def get_ingestion_job(job_id: UUID) -> IngestionJobRead:
    with SessionLocal() as session:
        return DocumentIngestionService(session, settings=get_settings()).get_job(job_id)


@router.post("/jobs/{job_id}/retry", response_model=IngestionRetryResponse)
async def retry_ingestion_job(job_id: UUID) -> IngestionRetryResponse:
    with SessionLocal() as session:
        return await DocumentIngestionService(session, settings=get_settings()).retry_failed_items(
            job_id
        )
