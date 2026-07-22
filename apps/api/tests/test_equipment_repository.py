from app.models.enums import Criticality, OperationalStatus
from app.repositories.equipment import EquipmentRepository
from app.schemas.equipment import EquipmentCreate


def test_equipment_repository_upserts_and_lists_by_filters(db_session) -> None:
    repository = EquipmentRepository(db_session)
    repository.upsert_by_tag(
        EquipmentCreate(
            equipment_tag="P-101",
            name="Feed Pump A",
            equipment_class="centrifugal_pump",
            site="Plant-1",
            system="Feedwater",
            criticality=Criticality.SAFETY_CRITICAL,
            operational_status=OperationalStatus.ACTIVE,
        )
    )
    repository.upsert_by_tag(
        EquipmentCreate(
            equipment_tag="C-201",
            name="Air Compressor",
            equipment_class="compressor",
            site="Plant-1",
            system="Utilities",
            criticality=Criticality.HIGH,
            operational_status=OperationalStatus.STANDBY,
        )
    )
    db_session.commit()

    items, total = repository.list(system="Feedwater")

    assert total == 1
    assert items[0].equipment_tag == "P-101"


def test_equipment_repository_updates_existing_tag(db_session) -> None:
    repository = EquipmentRepository(db_session)
    payload = EquipmentCreate(equipment_tag="P-101", name="Feed Pump A")
    repository.upsert_by_tag(payload)
    repository.upsert_by_tag(payload.model_copy(update={"name": "Feed Pump Alpha"}))
    db_session.commit()

    items, total = repository.list()

    assert total == 1
    assert items[0].name == "Feed Pump Alpha"
