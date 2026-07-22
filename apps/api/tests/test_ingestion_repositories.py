from datetime import UTC, datetime

from app.models.documents import Document
from app.models.enums import IngestionItemStatus, JobStatus, ParseStatus
from app.models.jobs import IngestionItem, IngestionJob
from app.repositories.documents import DocumentRepository
from app.repositories.ingestion import IngestionItemRepository, IngestionJobRepository


def test_document_repository_create_lookup_and_filters(db_session) -> None:
    repository = DocumentRepository(db_session)
    document = repository.create(
        Document(
            document_code="DOC-TEST-1",
            original_filename="manual.pdf",
            stored_filename="safe/key.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            source_type="manual",
            sha256="a" * 64,
            file_size_bytes=12,
            parse_status=ParseStatus.REGISTERED.value,
            uploaded_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    assert repository.get_by_id(document.id) == document
    assert repository.get_by_sha256("a" * 64) == document
    assert repository.checksum_exists("a" * 64)

    items, total = repository.list(search="manual", file_type="pdf", source_type="manual")

    assert total == 1
    assert items == [document]


def test_ingestion_repositories_track_job_item_and_duplicate(db_session) -> None:
    job_repository = IngestionJobRepository(db_session)
    item_repository = IngestionItemRepository(db_session)
    document_repository = DocumentRepository(db_session)
    job = job_repository.create(IngestionJob(status=JobStatus.PROCESSING.value, total_files=1))
    document = document_repository.create(
        Document(
            document_code="DOC-DUP",
            original_filename="manual.pdf",
            sha256="b" * 64,
            parse_status=ParseStatus.REGISTERED.value,
        )
    )
    db_session.flush()
    item = item_repository.create(
        IngestionItem(ingestion_job_id=job.id, original_filename="copy.pdf")
    )
    item_repository.increment_attempt_count(item)
    item_repository.mark_duplicate(item, document.id)
    db_session.commit()

    loaded_job = job_repository.get_with_items(job.id)

    assert loaded_job is not None
    assert loaded_job.items[0].status == IngestionItemStatus.DUPLICATE.value
    assert loaded_job.items[0].duplicate_of_document_id == document.id
    assert job_repository.list_items_for_job(job.id)[0].attempt_count == 1
