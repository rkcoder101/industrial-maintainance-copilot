from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

ComponentStatus = Literal["ok", "degraded", "down"]


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class ComponentHealth(BaseModel):
    name: str
    status: ComponentStatus
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    status: ComponentStatus
    service: str
    version: str = "0.1.0"
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    components: list[ComponentHealth]
