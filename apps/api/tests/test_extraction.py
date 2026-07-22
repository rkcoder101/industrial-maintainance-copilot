from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.assets import Equipment
from app.models.documents import Chunk, Document
from app.models.enums import Criticality, ParseStatus
from app.models.events import Event, Measurement
from app.models.jobs import ExtractedFact
from app.models.maintenance import MaintenanceAction, WorkOrder
from app.services.extraction import DocumentExtractionService
from app.services.extraction_errors import ExtractionNotReadyError, ExtractionRetryNotAllowedError


def _settings() -> Settings:
    return Settings(
        app_env="test",
        extraction_provider="mock",
        extraction_min_confidence=0.55,
        extraction_auto_accept_confidence=0.85,
    )


def _document(
    db_session: Session, text: str, *, status: str = ParseStatus.COMPLETED.value
) -> Document:
    equipment = Equipment(
        equipment_tag="P-101",
        name="Feed Pump A",
        criticality=Criticality.HIGH.value,
    )
    document_id = uuid4()
    document = Document(
        id=document_id,
        document_code=f"DOC-{document_id.hex[:12].upper()}",
        original_filename="p101.txt",
        file_type="txt",
        mime_type="text/plain",
        parse_status=status,
        page_count=1,
    )
    chunk = Chunk(
        document_id=document_id,
        chunk_index=0,
        chunk_kind="maintenance_record",
        first_page_number=1,
        last_page_number=1,
        text_content=text,
        citation_label=f"{document.document_code}:p1:c1",
        equipment_hint="P-101",
    )
    db_session.add_all([equipment, document, chunk])
    db_session.commit()
    return document


def test_mock_extraction_persists_validated_canonical_facts(db_session: Session) -> None:
    document = _document(
        db_session,
        "WO-8842 completed for P-101. Seal leak failure resolved. "
        "Pressure: 42 psi. Replaced seal and inspected bearing.",
    )

    response = DocumentExtractionService(db_session, settings=_settings()).extract_document(
        document.id
    )

    assert response.status.latest_run is not None
    assert response.status.latest_run.status == "completed"
    assert response.status.accepted_fact_count >= 5
    assert db_session.query(WorkOrder).count() == 1
    assert db_session.query(Event).count() >= 1
    assert db_session.query(Measurement).count() == 1
    assert db_session.query(MaintenanceAction).count() == 1
    assert db_session.query(ExtractedFact).filter_by(status="accepted").count() >= 5


def test_extraction_is_idempotent_without_force(db_session: Session) -> None:
    document = _document(db_session, "WO-1234 completed for P-101. Pressure: 44 psi.")
    service = DocumentExtractionService(db_session, settings=_settings())

    first = service.extract_document(document.id)
    second = service.extract_document(document.id)

    assert first.status.latest_run is not None
    assert second.status.latest_run is not None
    assert first.status.latest_run.id == second.status.latest_run.id
    assert db_session.query(WorkOrder).count() == 1
    assert db_session.query(Measurement).count() == 1


def test_force_extraction_records_duplicate_facts_without_canonical_duplicates(
    db_session: Session,
) -> None:
    document = _document(db_session, "WO-2222 completed for P-101. Pressure: 45 psi.")
    service = DocumentExtractionService(db_session, settings=_settings())

    service.extract_document(document.id)
    second = service.extract_document(document.id, force=True)

    assert second.status.latest_run is not None
    assert second.status.latest_run.duplicate_fact_count >= 1
    assert db_session.query(WorkOrder).count() == 1
    assert db_session.query(Measurement).count() == 1


def test_unparsed_document_cannot_be_extracted(db_session: Session) -> None:
    document = _document(db_session, "P-101 pending parse.", status=ParseStatus.REGISTERED.value)

    with pytest.raises(ExtractionNotReadyError):
        DocumentExtractionService(db_session, settings=_settings()).extract_document(document.id)


def test_retry_requires_failed_or_partial_run(db_session: Session) -> None:
    document = _document(db_session, "WO-3333 completed for P-101.")
    service = DocumentExtractionService(db_session, settings=_settings())
    service.extract_document(document.id)

    with pytest.raises(ExtractionRetryNotAllowedError):
        service.retry_document(document.id)


def test_low_confidence_fact_is_rejected_by_validation(db_session: Session) -> None:
    document = _document(db_session, "P-101 has a vague issue.")
    settings = _settings()
    settings.extraction_min_confidence = 0.99

    response = DocumentExtractionService(db_session, settings=settings).extract_document(
        document.id
    )

    assert response.status.latest_run is not None
    assert response.status.latest_run.rejected_fact_count >= 1
    assert db_session.query(ExtractedFact).filter_by(status="rejected").count() >= 1


def test_canonical_writes_include_provenance(db_session: Session) -> None:
    document = _document(db_session, "WO-4444 completed for P-101. Pressure: 46 psi.")

    DocumentExtractionService(db_session, settings=_settings()).extract_document(document.id)

    measurement = db_session.query(Measurement).one()
    assert measurement.source_document_id == document.id
    assert measurement.source_chunk_id is not None
    assert measurement.evidence_span is not None
    assert measurement.extracted_at is not None


def test_mock_provider_requires_no_api_key_or_network(db_session: Session) -> None:
    document = _document(db_session, "WO-5555 completed for P-101 at 47 psi.")
    settings = _settings()
    settings.extraction_api_key = None

    DocumentExtractionService(db_session, settings=settings).extract_document(document.id)

    run = db_session.query(ExtractedFact).first()
    assert run is not None
    assert "api_key" not in str(run.raw_payload_json).lower()


def test_extraction_does_not_create_embeddings_or_qdrant_records(db_session: Session) -> None:
    document = _document(db_session, "WO-6666 completed for P-101. Pressure: 48 psi.")

    response = DocumentExtractionService(db_session, settings=_settings()).extract_document(
        document.id
    )

    assert response.status.latest_run is not None
    assert response.status.latest_run.metadata_json["qdrant_indexed"] is False
    assert "embedding" not in str(response.status.latest_run.metadata_json).lower()


def test_rejected_unresolved_equipment_fact_is_audited(db_session: Session) -> None:
    document_id = uuid4()
    document = Document(
        id=document_id,
        document_code=f"DOC-{document_id.hex[:12].upper()}",
        original_filename="unknown.txt",
        file_type="txt",
        mime_type="text/plain",
        parse_status=ParseStatus.COMPLETED.value,
        page_count=1,
    )
    chunk = Chunk(
        document_id=document_id,
        chunk_index=0,
        chunk_kind="incident",
        first_page_number=1,
        last_page_number=1,
        text_content="P-999 vibration failure at 12 mm/s.",
        citation_label=f"{document.document_code}:p1:c1",
    )
    db_session.add_all([document, chunk])
    db_session.commit()

    DocumentExtractionService(db_session, settings=_settings()).extract_document(document.id)

    rejected = db_session.query(ExtractedFact).filter_by(status="rejected").all()
    assert rejected
    assert {fact.rejection_reason for fact in rejected} == {"equipment_unresolved"}


def test_date_import_keeps_timezone_dependency_visible() -> None:
    assert datetime.now(UTC).tzinfo is not None
