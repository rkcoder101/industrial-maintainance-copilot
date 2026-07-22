import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_parses_cors_origins() -> None:
    settings = Settings(cors_origins="http://localhost:3000, http://127.0.0.1:3000")

    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_settings_validates_upload_size() -> None:
    settings = Settings(max_upload_mb=25)

    assert settings.max_upload_mb == 25


def test_settings_validates_upload_batch_size() -> None:
    settings = Settings(max_batch_files=10)

    assert settings.max_batch_files == 10


def test_settings_rejects_invalid_upload_limits() -> None:
    with pytest.raises(ValidationError):
        Settings(max_upload_mb=0)
    with pytest.raises(ValidationError):
        Settings(max_batch_files=0)


def test_settings_normalizes_upload_extensions() -> None:
    settings = Settings(allowed_upload_extensions="pdf, .TXT, csv, pdf")

    assert settings.allowed_upload_extensions == ".pdf,.txt,.csv"
    assert settings.allowed_upload_extension_set == frozenset({".pdf", ".txt", ".csv"})


def test_settings_exposes_upload_paths(tmp_path) -> None:
    settings = Settings(upload_dir=str(tmp_path / "uploads"))

    assert settings.upload_root_path == (tmp_path / "uploads").resolve()
    assert settings.upload_temp_path == (tmp_path / "uploads" / ".tmp").resolve()
