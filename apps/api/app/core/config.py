from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "Industrial Maintenance Knowledge Copilot"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+psycopg://maintenance:maintenance@localhost:5432/maintenance_copilot"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    upload_dir: str = "/app/data/uploads"
    parsed_dir: str = "/app/data/parsed"
    rendered_pages_dir: str = "/app/data/rendered-pages"
    max_upload_mb: int = Field(default=50, ge=1)

    secret_key: str = "replace-this-in-real-environments"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
