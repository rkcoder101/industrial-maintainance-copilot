from collections.abc import AsyncIterator, Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

import app.api.v1.documents as document_routes
import app.api.v1.extraction as extraction_routes
import app.api.v1.ingestion as ingestion_routes
from app.core.config import Settings
from app.main import app
from app.models.assets import Equipment
from app.models.enums import Criticality
from tests.ingestion_helpers import valid_pdf_bytes


@pytest.fixture
def extraction_api_session(
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session, None, None]:
    settings = Settings(
        app_env="test",
        upload_dir=str(tmp_path / "uploads"),
        parsed_dir=str(tmp_path / "parsed"),
        rendered_pages_dir=str(tmp_path / "rendered-pages"),
        ocr_enabled=False,
        extraction_provider="mock",
    )

    class TestSessionLocal:
        def __enter__(self) -> Session:
            return db_session

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(ingestion_routes, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(document_routes, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(extraction_routes, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(ingestion_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(document_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(extraction_routes, "get_settings", lambda: settings)
    db_session.add(
        Equipment(
            equipment_tag="P-101",
            name="Feed Pump A",
            criticality=Criticality.HIGH.value,
        )
    )
    db_session.commit()
    yield db_session


async def _client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_extraction_api_exposes_status_runs_and_facts(
    extraction_api_session: Session,
) -> None:
    async for client in _client():
        upload = await client.post(
            "/api/v1/ingestion/documents",
            files={
                "files": (
                    "p101.pdf",
                    valid_pdf_bytes(
                        [
                            "WO-9901 completed for P-101. Seal leak failure resolved. "
                            "Pressure: 51 psi."
                        ]
                    ),
                    "application/pdf",
                )
            },
            data={"source_type": "work_order"},
        )
        document_id = upload.json()["items"][0]["document_id"]
        await client.post(f"/api/v1/documents/{document_id}/process")
        extract = await client.post(f"/api/v1/documents/{document_id}/extract")
        status = await client.get(f"/api/v1/documents/{document_id}/extraction")
        runs = await client.get(f"/api/v1/documents/{document_id}/extraction/runs")
        run_id = runs.json()[0]["id"]
        run = await client.get(f"/api/v1/extraction/runs/{run_id}")
        facts = await client.get(f"/api/v1/extraction/runs/{run_id}/facts")
        fact = await client.get(f"/api/v1/extraction/facts/{facts.json()['items'][0]['id']}")
        retry = await client.post(f"/api/v1/documents/{document_id}/extract/retry")

    assert extract.status_code == 200
    assert extract.json()["status"]["latest_run"]["model_provider"] == "mock"
    assert status.status_code == 200
    assert status.json()["accepted_fact_count"] >= 1
    assert runs.status_code == 200
    assert len(runs.json()) == 1
    assert run.status_code == 200
    assert run.json()["id"] == run_id
    assert facts.status_code == 200
    assert facts.json()["total"] >= 1
    assert fact.status_code == 200
    assert "raw_payload_json" not in fact.text
    assert retry.status_code == 409
    assert retry.json()["error"]["code"] == "extraction_retry_not_allowed"
