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
