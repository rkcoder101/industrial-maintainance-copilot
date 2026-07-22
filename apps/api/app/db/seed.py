import json
from pathlib import Path

from app.db.session import SessionLocal
from app.repositories.equipment import EquipmentRepository
from app.schemas.equipment import EquipmentCreate


def seed_equipment(seed_path: Path | None = None) -> int:
    path = seed_path or Path(__file__).resolve().parents[4] / "data" / "seeds" / "equipment.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    with SessionLocal() as session:
        repository = EquipmentRepository(session)
        for item in payload:
            repository.upsert_by_tag(EquipmentCreate.model_validate(item))
        session.commit()
        return len(payload)


def main() -> None:
    count = seed_equipment()
    print(f"Seeded {count} equipment records.")


if __name__ == "__main__":
    main()
