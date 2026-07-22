from pathlib import Path

from app.models import Base


def test_initial_migration_creates_all_model_tables() -> None:
    api_root = Path(__file__).resolve().parents[1]
    migration_files = list(
        (api_root / "alembic" / "versions").glob("*_create_canonical_data_model.py")
    )
    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text(encoding="utf-8")

    for table_name in Base.metadata.tables:
        assert f'create_table(\n        "{table_name}"' in migration_text
