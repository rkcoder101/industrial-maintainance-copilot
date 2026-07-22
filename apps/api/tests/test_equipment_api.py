from collections.abc import AsyncIterator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

import app.api.v1.equipment as equipment_routes
from app.main import app
from app.repositories.equipment import EquipmentRepository
from app.schemas.equipment import EquipmentCreate


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def equipment_api_session(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session, None, None]:
    repository = EquipmentRepository(db_session)
    repository.upsert_by_tag(EquipmentCreate(equipment_tag="P-101", name="Feed Pump A"))
    db_session.commit()

    class TestSessionLocal:
        def __enter__(self):
            return db_session

        def __exit__(self, *_) -> None:
            return None

    monkeypatch.setattr(equipment_routes, "SessionLocal", TestSessionLocal)
    yield db_session


async def _client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_list_equipment_endpoint(equipment_api_session: Session) -> None:
    async for client in _client():
        response = await client.get("/api/v1/equipment/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["equipment_tag"] == "P-101"


@pytest.mark.anyio
async def test_get_equipment_by_tag_endpoint(equipment_api_session: Session) -> None:
    async for client in _client():
        response = await client.get("/api/v1/equipment/P-101")

    assert response.status_code == 200
    assert response.json()["name"] == "Feed Pump A"


@pytest.mark.anyio
async def test_missing_equipment_uses_error_shape(equipment_api_session: Session) -> None:
    async for client in _client():
        response = await client.get("/api/v1/equipment/NOPE")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Equipment not found."
