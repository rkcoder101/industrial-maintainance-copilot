from pathlib import Path

from app.models import Base


def test_initial_migration_creates_all_model_tables() -> None:
    api_root = Path(__file__).resolve().parents[1]
    migration_files = list((api_root / "alembic" / "versions").glob("*.py"))
    assert migration_files
    migration_text = "\n".join(
        migration_file.read_text(encoding="utf-8") for migration_file in migration_files
    )

    for table_name in Base.metadata.tables:
        assert f'create_table(\n        "{table_name}"' in migration_text
