from collections.abc import AsyncIterator, Generator
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

import app.api.v1.documents as document_routes
import app.api.v1.ingestion as ingestion_routes
from app.core.config import Settings
from app.main import app
from app.models.documents import Document
from app.models.enums import ParseStatus
from tests.ingestion_helpers import valid_pdf_bytes


@pytest.fixture
def processing_api_session(
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session, None, None]:
    settings = Settings(
        app_env="test",
        upload_dir=str(tmp_path / "uploads"),
        parsed_dir=str(tmp_path / "parsed"),
        rendered_pages_dir=str(tmp_path / "rendered-pages"),
        max_batch_files=3,
        ocr_enabled=False,
    )

    class TestSessionLocal:
        def __enter__(self) -> Session:
            return db_session

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(ingestion_routes, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(document_routes, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(ingestion_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(document_routes, "get_settings", lambda: settings)
    yield db_session


async def _client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_process_pdf_exposes_pages_chunks_runs_and_images(
    processing_api_session: Session,
) -> None:
    async for client in _client():
        upload_response = await client.post(
            "/api/v1/ingestion/documents",
            files={
                "files": (
                    "manual.pdf",
                    valid_pdf_bytes(["P-101 PUMP\nInspect seal pressure before startup."]),
                    "application/pdf",
                )
            },
            data={"source_type": "manual"},
        )
        document_id = upload_response.json()["items"][0]["document_id"]

        process_response = await client.post(f"/api/v1/documents/{document_id}/process")
        pages_response = await client.get(f"/api/v1/documents/{document_id}/pages")
        page_response = await client.get(f"/api/v1/documents/{document_id}/pages/1")
        image_response = await client.get(f"/api/v1/documents/{document_id}/pages/1/image")
        chunks_response = await client.get(f"/api/v1/documents/{document_id}/chunks")
        runs_response = await client.get(f"/api/v1/documents/{document_id}/processing/runs")

    assert process_response.status_code == 200
    status = process_response.json()["status"]
    assert status["document"]["parse_status"] == "completed_with_warnings"
    assert status["page_count"] == 1
    assert status["block_count"] >= 1
    assert status["chunk_count"] >= 1
    assert pages_response.status_code == 200
    assert pages_response.json()[0]["has_rendered_image"] is True
    assert "rendered-pages" not in str(pages_response.json())
    assert ".tmp" not in str(pages_response.json())
    assert page_response.status_code == 200
    assert page_response.json()["blocks"]
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"
    assert chunks_response.status_code == 200
    assert chunks_response.json()["items"][0]["citation_label"].startswith(
        status["document"]["document_code"]
    )
    assert runs_response.status_code == 200
    assert len(runs_response.json()) == 1


@pytest.mark.anyio
async def test_force_reprocess_replaces_artifacts_and_preserves_runs(
    processing_api_session: Session,
) -> None:
    async for client in _client():
        upload_response = await client.post(
            "/api/v1/ingestion/documents",
            files={"files": ("manual.pdf", valid_pdf_bytes(), "application/pdf")},
        )
        document_id = upload_response.json()["items"][0]["document_id"]
        await client.post(f"/api/v1/documents/{document_id}/process")
        await client.post(f"/api/v1/documents/{document_id}/process", params={"force": "true"})
        pages_response = await client.get(f"/api/v1/documents/{document_id}/pages")
        chunks_response = await client.get(f"/api/v1/documents/{document_id}/chunks")
        runs_response = await client.get(f"/api/v1/documents/{document_id}/processing/runs")

    assert pages_response.status_code == 200
    assert len(pages_response.json()) == 1
    assert chunks_response.json()["total"] >= 1
    assert len(runs_response.json()) == 2


@pytest.mark.anyio
async def test_retry_is_rejected_for_completed_document(processing_api_session: Session) -> None:
    async for client in _client():
        upload_response = await client.post(
            "/api/v1/ingestion/documents",
            files={"files": ("manual.pdf", valid_pdf_bytes(), "application/pdf")},
        )
        document_id = upload_response.json()["items"][0]["document_id"]
        await client.post(f"/api/v1/documents/{document_id}/process")
        retry_response = await client.post(f"/api/v1/documents/{document_id}/process/retry")

    assert retry_response.status_code == 409
    assert retry_response.json()["error"]["code"] == "processing_retry_not_allowed"


@pytest.mark.anyio
async def test_failed_processing_can_be_retried_with_run_history(
    processing_api_session: Session,
) -> None:
    document_id = uuid4()
    processing_api_session.add(
        Document(
            id=document_id,
            document_code=f"DOC-{document_id.hex[:12].upper()}",
            original_filename="missing.pdf",
            stored_filename=f"{document_id.hex[:4]}/{document_id}/missing.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            parse_status=ParseStatus.REGISTERED.value,
        )
    )
    processing_api_session.commit()

    async for client in _client():
        first = await client.post(f"/api/v1/documents/{document_id}/process")
        retry = await client.post(f"/api/v1/documents/{document_id}/process/retry")
        runs = await client.get(f"/api/v1/documents/{document_id}/processing/runs")

    assert first.status_code == 404
    assert first.json()["error"]["code"] == "stored_document_missing"
    assert retry.status_code == 404
    assert retry.json()["error"]["code"] == "stored_document_missing"
    assert len(runs.json()) == 2
    assert {run["status"] for run in runs.json()} == {"failed"}
