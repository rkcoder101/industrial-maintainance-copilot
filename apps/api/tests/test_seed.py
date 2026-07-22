import json
from pathlib import Path

import app.db.seed as seed_module
from app.repositories.equipment import EquipmentRepository


def test_seed_equipment_is_idempotent(db_session, tmp_path: Path, monkeypatch) -> None:
    seed_path = tmp_path / "equipment.json"
    seed_path.write_text(
        json.dumps(
            [
                {
                    "equipment_tag": "P-101",
                    "name": "Feed Pump A",
                    "criticality": "high",
                    "operational_status": "active",
                }
            ]
        ),
        encoding="utf-8",
    )

    class TestSessionLocal:
        def __enter__(self):
            return db_session

        def __exit__(self, *_) -> None:
            return None

    monkeypatch.setattr(seed_module, "SessionLocal", TestSessionLocal)

    assert seed_module.seed_equipment(seed_path) == 1
    assert seed_module.seed_equipment(seed_path) == 1
    _, total = EquipmentRepository(db_session).list()
    assert total == 1
