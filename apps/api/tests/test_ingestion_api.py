from collections.abc import AsyncIterator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

import app.api.v1.documents as document_routes
import app.api.v1.ingestion as ingestion_routes
from app.core.config import Settings
from app.main import app
from tests.ingestion_helpers import csv_bytes, pdf_bytes


@pytest.fixture
def ingestion_api_session(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session, None, None]:
    settings = Settings(app_env="test", upload_dir=str(tmp_path / "uploads"), max_batch_files=2)

    class TestSessionLocal:
        def __enter__(self):
            return db_session

        def __exit__(self, *_) -> None:
            return None

    monkeypatch.setattr(ingestion_routes, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(document_routes, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(ingestion_routes, "get_settings", lambda: settings)
    yield db_session


async def _client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_upload_one_file_and_get_document(ingestion_api_session: Session) -> None:
    async for client in _client():
        upload_response = await client.post(
            "/api/v1/ingestion/documents",
            files={"files": ("manual.pdf", pdf_bytes(), "application/pdf")},
            data={"source_type": "manual"},
        )
        document_id = upload_response.json()["items"][0]["document_id"]
        document_response = await client.get(f"/api/v1/documents/{document_id}")

    assert upload_response.status_code == 202
    assert upload_response.json()["job"]["processed_files"] == 1
    assert document_response.status_code == 200
    payload = document_response.json()
    assert payload["original_filename"] == "manual.pdf"
    assert payload["parse_status"] == "registered"
    assert "stored_filename" not in payload
    assert "uploads" not in str(payload)


@pytest.mark.anyio
async def test_upload_mixed_batch_and_retrieve_job(ingestion_api_session: Session) -> None:
    async for client in _client():
        upload_response = await client.post(
            "/api/v1/ingestion/documents",
            files=[
                ("files", ("inspection.csv", csv_bytes(), "text/csv")),
                ("files", ("bad.pdf", b"not a pdf", "application/pdf")),
            ],
            data={"source_type": "inspection"},
        )
        job_id = upload_response.json()["job"]["id"]
        job_response = await client.get(f"/api/v1/ingestion/jobs/{job_id}")

    assert upload_response.status_code == 202
    assert upload_response.json()["job"]["status"] == "completed_with_errors"
    assert job_response.status_code == 200
    assert len(job_response.json()["items"]) == 2


@pytest.mark.anyio
async def test_upload_duplicate_reports_duplicate(ingestion_api_session: Session) -> None:
    async for client in _client():
        first = await client.post(
            "/api/v1/ingestion/documents",
            files={"files": ("manual.pdf", pdf_bytes(), "application/pdf")},
        )
        duplicate = await client.post(
            "/api/v1/ingestion/documents",
            files={"files": ("copy.pdf", pdf_bytes(), "application/pdf")},
        )

    assert first.status_code == 202
    assert duplicate.status_code == 202
    item = duplicate.json()["items"][0]
    assert item["status"] == "duplicate"
    assert item["duplicate_of_document_id"] == first.json()["items"][0]["document_id"]


@pytest.mark.anyio
async def test_upload_missing_files_uses_stable_error_code(
    ingestion_api_session: Session,
) -> None:
    async for client in _client():
        response = await client.post("/api/v1/ingestion/documents")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_file_type"


@pytest.mark.anyio
async def test_upload_batch_too_large_uses_stable_error_code(
    ingestion_api_session: Session,
) -> None:
    async for client in _client():
        response = await client.post(
            "/api/v1/ingestion/documents",
            files=[
                ("files", ("a.pdf", pdf_bytes(), "application/pdf")),
                ("files", ("b.pdf", pdf_bytes(), "application/pdf")),
                ("files", ("c.pdf", pdf_bytes(), "application/pdf")),
            ],
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "batch_too_large"


@pytest.mark.anyio
async def test_list_documents_filters_and_paginates(ingestion_api_session: Session) -> None:
    async for client in _client():
        await client.post(
            "/api/v1/ingestion/documents",
            files={"files": ("inspection.csv", csv_bytes(), "text/csv")},
            data={"source_type": "inspection"},
        )
        response = await client.get(
            "/api/v1/documents",
            params={"file_type": "csv", "source_type": "inspection", "page": 1, "page_size": 10},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["file_type"] == "csv"


@pytest.mark.anyio
async def test_missing_job_and_document_use_stable_errors(ingestion_api_session: Session) -> None:
    missing_uuid = "00000000-0000-0000-0000-000000000000"

    async for client in _client():
        job_response = await client.get(f"/api/v1/ingestion/jobs/{missing_uuid}")
        document_response = await client.get(f"/api/v1/documents/{missing_uuid}")
        retry_response = await client.post(f"/api/v1/ingestion/jobs/{missing_uuid}/retry")

    assert job_response.status_code == 404
    assert job_response.json()["error"]["code"] == "ingestion_job_not_found"
    assert document_response.status_code == 404
    assert document_response.json()["error"]["code"] == "document_not_found"
    assert retry_response.status_code == 404
    assert retry_response.json()["error"]["code"] == "ingestion_job_not_found"
