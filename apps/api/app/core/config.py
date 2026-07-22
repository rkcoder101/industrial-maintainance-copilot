from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ALLOWED_UPLOAD_EXTENSIONS = ".pdf,.docx,.xlsx,.csv,.txt,.png,.jpg,.jpeg"


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

    database_url: str = (
        "postgresql+psycopg://maintenance:maintenance@localhost:5432/maintenance_copilot"
    )
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    upload_dir: str = "/app/data/uploads"
    parsed_dir: str = "/app/data/parsed"
    rendered_pages_dir: str = "/app/data/rendered-pages"
    max_upload_mb: int = Field(default=50, ge=1)
    max_batch_files: int = Field(default=20, ge=1)
    allowed_upload_extensions: str = DEFAULT_ALLOWED_UPLOAD_EXTENSIONS
    ocr_enabled: bool = True
    ocr_language: str = "eng"
    ocr_min_text_characters: int = Field(default=30, ge=0)
    page_render_dpi: int = Field(default=150, ge=72, le=300)
    chunk_target_tokens: int = Field(default=500, gt=0)
    chunk_max_tokens: int = Field(default=800, gt=0)
    chunk_overlap_tokens: int = Field(default=75, ge=0)
    extraction_enabled: bool = True
    extraction_provider: Literal["mock", "ollama"] = "mock"
    extraction_model: str = "maintenance-extraction-mock"
    extraction_api_base_url: str | None = None
    extraction_api_key: str | None = None
    extraction_timeout_seconds: int = Field(default=30, ge=1, le=300)
    extraction_max_retries: int = Field(default=2, ge=0, le=5)
    extraction_concurrency: int = Field(default=1, ge=1, le=8)
    extraction_min_confidence: float = Field(default=0.55, ge=0, le=1)
    extraction_auto_accept_confidence: float = Field(default=0.85, ge=0, le=1)
    extraction_max_chunk_characters: int = Field(default=6000, ge=500, le=20000)
    extraction_prompt_version: str = "maintenance_extraction_v1"
    ollama_base_url: str = "http://localhost:11434"

    secret_key: str = "replace-this-in-real-environments"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_root_path(self) -> Path:
        return Path(self.upload_dir).expanduser().resolve()

    @property
    def upload_temp_path(self) -> Path:
        return self.upload_root_path / ".tmp"

    @property
    def rendered_pages_root_path(self) -> Path:
        return Path(self.rendered_pages_dir).expanduser().resolve()

    @property
    def rendered_pages_temp_path(self) -> Path:
        return self.rendered_pages_root_path / ".tmp"

    @property
    def parsed_root_path(self) -> Path:
        return Path(self.parsed_dir).expanduser().resolve()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def allowed_upload_extension_set(self) -> frozenset[str]:
        return frozenset(
            extension.strip().lower()
            for extension in self.allowed_upload_extensions.split(",")
            if extension.strip()
        )

    @field_validator("allowed_upload_extensions")
    @classmethod
    def validate_allowed_upload_extensions(cls, value: str) -> str:
        normalized: list[str] = []
        for raw_extension in value.split(","):
            extension = raw_extension.strip().lower()
            if not extension:
                continue
            if "/" in extension or "\\" in extension or "\x00" in extension:
                raise ValueError("upload extensions cannot contain path separators or null bytes")
            if not extension.startswith("."):
                extension = f".{extension}"
            if extension == ".":
                raise ValueError("upload extensions cannot be empty")
            normalized.append(extension)
        if not normalized:
            raise ValueError("at least one upload extension must be configured")
        return ",".join(dict.fromkeys(normalized))

    @field_validator("ocr_language")
    @classmethod
    def validate_ocr_language(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("OCR language cannot be empty")
        if any(character in normalized for character in "/\\\x00"):
            raise ValueError("OCR language cannot contain path separators or null bytes")
        return normalized

    def model_post_init(self, __context: object) -> None:
        if self.chunk_max_tokens < self.chunk_target_tokens:
            raise ValueError(
                "CHUNK_MAX_TOKENS must be greater than or equal to CHUNK_TARGET_TOKENS"
            )
        if self.chunk_overlap_tokens >= self.chunk_max_tokens:
            raise ValueError("CHUNK_OVERLAP_TOKENS must be less than CHUNK_MAX_TOKENS")
        if self.extraction_auto_accept_confidence < self.extraction_min_confidence:
            raise ValueError(
                "EXTRACTION_AUTO_ACCEPT_CONFIDENCE must be greater than or equal to "
                "EXTRACTION_MIN_CONFIDENCE"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
