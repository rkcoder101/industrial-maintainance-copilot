from pathlib import Path

import pytest

from app.core.config import Settings
from app.models.documents import Document
from app.models.enums import IngestionItemStatus, JobStatus, ParseStatus
from app.repositories.documents import DocumentRepository
from app.services.ingestion import DocumentIngestionService
from app.services.ingestion_errors import StorageOperationError
from app.services.storage import DocumentStorageService, LocalStorageBackend
from tests.ingestion_helpers import csv_bytes, pdf_bytes, upload_file


def settings_for_uploads(upload_root: Path, *, max_upload_mb: int = 50) -> Settings:
    return Settings(
        app_env="test",
        upload_dir=str(upload_root),
        max_upload_mb=max_upload_mb,
        max_batch_files=20,
    )


@pytest.mark.anyio
async def test_ingestion_service_registers_one_valid_file(db_session, tmp_path) -> None:
    service = DocumentIngestionService(
        db_session,
        settings=settings_for_uploads(tmp_path / "uploads"),
    )

    result = await service.upload_documents(
        files=[upload_file("manual.pdf", pdf_bytes())],
        source_type="manual",
    )

    assert result.job.status == JobStatus.COMPLETED
    assert result.job.processed_files == 1
    assert result.items[0].status == IngestionItemStatus.STORED
    assert result.items[0].document_id is not None

    document = DocumentRepository(db_session).get_by_id(result.items[0].document_id)
    assert document is not None
    assert document.parse_status == ParseStatus.REGISTERED.value
    assert document.stored_filename is not None
    assert (tmp_path / "uploads" / document.stored_filename).is_file()


@pytest.mark.anyio
async def test_ingestion_service_preserves_mixed_batch_results(db_session, tmp_path) -> None:
    service = DocumentIngestionService(
        db_session,
        settings=settings_for_uploads(tmp_path / "uploads"),
    )

    result = await service.upload_documents(
        files=[
            upload_file("inspection.csv", csv_bytes()),
            upload_file("bad.pdf", b"not a pdf"),
        ],
        source_type="maintenance_record",
    )

    statuses = {item.original_filename: item.status for item in result.items}
    assert result.job.status == JobStatus.COMPLETED_WITH_ERRORS
    assert result.job.processed_files == 1
    assert result.job.failed_files == 1
    assert statuses["inspection.csv"] == IngestionItemStatus.STORED
    assert statuses["bad.pdf"] == IngestionItemStatus.FAILED


@pytest.mark.anyio
async def test_ingestion_service_marks_all_invalid_batch_failed(db_session, tmp_path) -> None:
    service = DocumentIngestionService(
        db_session,
        settings=settings_for_uploads(tmp_path / "uploads"),
    )

    result = await service.upload_documents(files=[upload_file("bad.exe", b"MZ")])

    assert result.job.status == JobStatus.FAILED
    assert result.job.failed_files == 1
    assert result.items[0].error_code == "unsupported_file_type"


@pytest.mark.anyio
async def test_ingestion_service_detects_duplicate_content(db_session, tmp_path) -> None:
    service = DocumentIngestionService(
        db_session,
        settings=settings_for_uploads(tmp_path / "uploads"),
    )
    first = await service.upload_documents(files=[upload_file("manual.pdf", pdf_bytes())])

    duplicate = await service.upload_documents(files=[upload_file("copy.pdf", pdf_bytes())])

    assert duplicate.job.status == JobStatus.COMPLETED
    assert duplicate.items[0].status == IngestionItemStatus.DUPLICATE
    assert duplicate.items[0].duplicate_of_document_id == first.items[0].document_id
    assert db_session.query(Document).count() == 1


@pytest.mark.anyio
async def test_ingestion_service_same_filename_different_content_is_new_document(
    db_session, tmp_path
) -> None:
    service = DocumentIngestionService(
        db_session,
        settings=settings_for_uploads(tmp_path / "uploads"),
    )

    first = await service.upload_documents(files=[upload_file("manual.pdf", pdf_bytes())])
    second = await service.upload_documents(
        files=[upload_file("manual.pdf", b"%PDF-1.7\nsecond file\n%%EOF\n")]
    )

    assert first.items[0].document_id != second.items[0].document_id
    assert db_session.query(Document).count() == 2


@pytest.mark.anyio
async def test_ingestion_service_enforces_actual_size_limit(db_session, tmp_path) -> None:
    service = DocumentIngestionService(
        db_session,
        settings=settings_for_uploads(tmp_path / "uploads", max_upload_mb=1),
    )

    result = await service.upload_documents(
        files=[upload_file("large.txt", b"a" * (1024 * 1024 + 1))]
    )

    assert result.job.status == JobStatus.FAILED
    assert result.items[0].error_code == "file_too_large"


class FailFirstFinalStorage(LocalStorageBackend):
    def __init__(self, upload_root: Path) -> None:
        super().__init__(upload_root)
        self.failed = False

    async def save(self, temp_path: Path, storage_key: str) -> str:
        if not self.failed and not storage_key.startswith(".quarantine/"):
            self.failed = True
            raise StorageOperationError()
        return await super().save(temp_path, storage_key)


@pytest.mark.anyio
async def test_ingestion_retry_registers_quarantined_post_validation_failure(
    db_session, tmp_path
) -> None:
    backend = FailFirstFinalStorage(tmp_path / "uploads")
    service = DocumentIngestionService(
        db_session,
        settings=settings_for_uploads(tmp_path / "uploads"),
        storage_service=DocumentStorageService(backend),
    )

    first = await service.upload_documents(files=[upload_file("manual.pdf", pdf_bytes())])

    assert first.job.status == JobStatus.FAILED
    assert first.items[0].error_code == "storage_operation_failed"

    retried = await service.retry_failed_items(first.job.id)

    assert retried.job.status == JobStatus.COMPLETED
    assert retried.retried_items[0].status == IngestionItemStatus.STORED
    assert retried.retried_items[0].document_id is not None
