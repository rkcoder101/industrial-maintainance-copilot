from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models import Base
from app.models.assets import Equipment
from app.models.enums import Criticality, EventType, OperationalStatus
from app.models.events import Event, FailureEvent
from app.models.jobs import IngestionItem, IngestionJob
from app.models.maintenance import WorkOrder


def test_canonical_metadata_contains_required_tables() -> None:
    assert {
        "equipment",
        "components",
        "documents",
        "document_pages",
        "chunks",
        "events",
        "failure_events",
        "measurements",
        "procedures",
        "maintenance_actions",
        "work_orders",
        "compliance_rules",
        "compliance_findings",
        "graph_edges",
        "citations",
        "ingestion_jobs",
        "ingestion_items",
        "extraction_runs",
    }.issubset(Base.metadata.tables)


def test_equipment_json_defaults_are_not_shared(db_session) -> None:
    first = Equipment(
        equipment_tag="P-101",
        name="Feed Pump A",
        criticality=Criticality.HIGH.value,
        operational_status=OperationalStatus.ACTIVE.value,
    )
    second = Equipment(
        equipment_tag="P-102",
        name="Feed Pump B",
        criticality=Criticality.MEDIUM.value,
        operational_status=OperationalStatus.STANDBY.value,
    )
    db_session.add_all([first, second])
    db_session.flush()

    first.metadata_json["note"] = "first only"

    assert second.metadata_json == {}


def test_event_rejects_end_time_before_start_time() -> None:
    started_at = datetime(2026, 7, 22, 8, tzinfo=UTC)

    with pytest.raises(ValueError, match="end_time"):
        Event(
            equipment_id="00000000-0000-0000-0000-000000000001",
            event_type=EventType.FAILURE.value,
            event_time=started_at,
            end_time=started_at - timedelta(minutes=1),
        )


def test_failure_event_requires_failure_type() -> None:
    event = Event(
        equipment_id="00000000-0000-0000-0000-000000000001",
        event_type=EventType.INSPECTION.value,
    )

    with pytest.raises(ValueError, match="type failure"):
        FailureEvent(event=event, failure_mode="seal_leak")


def test_work_order_rejects_completion_before_opening() -> None:
    opened_at = datetime(2026, 7, 22, 8, tzinfo=UTC)

    with pytest.raises(ValueError, match="completed_at"):
        WorkOrder(
            work_order_number="WO-1",
            equipment_id="00000000-0000-0000-0000-000000000001",
            title="Inspect pump",
            opened_at=opened_at,
            completed_at=opened_at - timedelta(minutes=1),
        )


def test_ingestion_job_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        IngestionJob(total_files=1, processed_files=1, failed_files=1)


def test_ingestion_item_rejects_invalid_counts_and_size() -> None:
    item = IngestionItem(ingestion_job_id=uuid4(), original_filename="manual.pdf")

    with pytest.raises(ValueError, match="attempt_count"):
        item.attempt_count = -1
    with pytest.raises(ValueError, match="actual_size_bytes"):
        item.actual_size_bytes = -1
