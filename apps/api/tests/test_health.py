from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.health import ComponentHealth, HealthResponse


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_liveness_endpoint() -> None:
    async for client in _client():
        response = await client.get("/api/v1/health/live")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_readiness_response_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_readiness(_) -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="Industrial Maintenance Knowledge Copilot",
            components=[
                ComponentHealth(name="api", status="ok"),
                ComponentHealth(name="postgres", status="ok"),
                ComponentHealth(name="qdrant", status="ok"),
            ],
        )

    monkeypatch.setattr("app.api.v1.health.build_readiness", fake_readiness)
    async for client in _client():
        response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert [component["name"] for component in payload["components"]] == [
            "api",
            "postgres",
            "qdrant",
        ]
