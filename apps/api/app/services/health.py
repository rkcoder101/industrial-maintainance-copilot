from time import perf_counter

import anyio
from qdrant_client import QdrantClient
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import create_db_engine
from app.schemas.health import ComponentHealth, ComponentStatus, HealthResponse


async def build_readiness(settings: Settings) -> HealthResponse:
    components = [
        ComponentHealth(name="api", status="ok", message="Application is running."),
        await check_postgres(settings),
        await check_qdrant(settings),
    ]
    status: ComponentStatus = (
        "ok" if all(component.status == "ok" for component in components) else "degraded"
    )
    return HealthResponse(
        status=status,
        service=settings.app_name,
        components=components,
    )


async def check_postgres(settings: Settings) -> ComponentHealth:
    return await anyio.to_thread.run_sync(_check_postgres_sync, settings)


def _check_postgres_sync(settings: Settings) -> ComponentHealth:
    started_at = perf_counter()
    try:
        engine = create_db_engine(settings)
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return ComponentHealth(
            name="postgres",
            status="ok",
            latency_ms=_elapsed_ms(started_at),
            message="PostgreSQL connection succeeded.",
        )
    except Exception as exc:  # noqa: BLE001 - health checks must report dependency failures.
        return ComponentHealth(
            name="postgres",
            status="down",
            latency_ms=_elapsed_ms(started_at),
            message=str(exc),
        )


async def check_qdrant(settings: Settings) -> ComponentHealth:
    return await anyio.to_thread.run_sync(_check_qdrant_sync, settings)


def _check_qdrant_sync(settings: Settings) -> ComponentHealth:
    started_at = perf_counter()
    try:
        client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        client.get_collections()
        return ComponentHealth(
            name="qdrant",
            status="ok",
            latency_ms=_elapsed_ms(started_at),
            message="Qdrant connection succeeded.",
        )
    except Exception as exc:  # noqa: BLE001 - health checks must report dependency failures.
        return ComponentHealth(
            name="qdrant",
            status="down",
            latency_ms=_elapsed_ms(started_at),
            message=str(exc),
        )


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)
