import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.documents import Document
from app.models.enums import IngestionItemStatus, JobStatus, ParseStatus
from app.models.jobs import IngestionItem, IngestionJob
from app.repositories.documents import DocumentRepository
from app.repositories.ingestion import IngestionItemRepository, IngestionJobRepository
from app.schemas.ingestion import (
    IngestionItemRead,
    IngestionJobRead,
    IngestionJobSummary,
    IngestionRetryResponse,
    IngestionUploadResponse,
)
from app.services.file_validation import FilenameValidationResult, FileValidationService
from app.services.ingestion_errors import (
    BatchTooLargeError,
    DatabaseRegistrationError,
    EmptyFileError,
    FileTooLargeError,
    IngestionError,
    IngestionItemNotRetryableError,
    IngestionJobNotFoundError,
    StorageOperationError,
    UnsupportedFileTypeError,
)
from app.services.scanner import FileScanner, NoopFileScanner
from app.services.storage import DocumentStorageService, LocalStorageBackend

STREAM_CHUNK_SIZE = 1024 * 1024
HEADER_BYTES = 8192


class DocumentIngestionService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings,
        storage_service: DocumentStorageService | None = None,
        scanner: FileScanner | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.document_repository = DocumentRepository(session)
        self.job_repository = IngestionJobRepository(session)
        self.item_repository = IngestionItemRepository(session)
        self.validation_service = FileValidationService(settings.allowed_upload_extension_set)
        self.storage_service = storage_service or DocumentStorageService(
            LocalStorageBackend(settings.upload_root_path)
        )
        self.scanner = scanner or NoopFileScanner()

    async def upload_documents(
        self,
        *,
        files: list[UploadFile] | None,
        source_type: str | None = None,
    ) -> IngestionUploadResponse:
        self._validate_batch(files)
        active_files = list(files or [])
        now = self._now()
        job = self.job_repository.create(
            IngestionJob(
                status=JobStatus.PROCESSING.value,
                total_files=len(active_files),
                started_at=now,
            )
        )
        self.session.flush()
        items = [
            self.item_repository.create(
                IngestionItem(
                    ingestion_job_id=job.id,
                    original_filename=(upload.filename or "").strip()[:512],
                )
            )
            for upload in active_files
        ]
        self.session.commit()

        for upload, item in zip(active_files, items, strict=True):
            await self._process_upload_item(upload, item.id, source_type=source_type)

        job = self._complete_job(job.id)
        items = self.job_repository.list_items_for_job(job.id)
        return IngestionUploadResponse(
            job=IngestionJobSummary.model_validate(job),
            items=[IngestionItemRead.model_validate(item) for item in items],
        )

    def get_job(self, job_id: UUID) -> IngestionJobRead:
        job = self.job_repository.get_with_items(job_id)
        if job is None:
            raise IngestionJobNotFoundError()
        return IngestionJobRead.model_validate(job)

    async def retry_failed_items(self, job_id: UUID) -> IngestionRetryResponse:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise IngestionJobNotFoundError()

        retryable_items = self.job_repository.get_retryable_failed_items(job_id)
        retryable_items = [
            item for item in retryable_items if item.metadata_json.get("quarantine_storage_key")
        ]
        if not retryable_items:
            raise IngestionItemNotRetryableError()

        retried: list[IngestionItem] = []
        for item in retryable_items:
            retried.append(await self._retry_quarantined_item(item.id))

        job = self._complete_job(job_id)
        return IngestionRetryResponse(
            job=IngestionJobSummary.model_validate(job),
            retried_items=[IngestionItemRead.model_validate(item) for item in retried],
            message="Retry attempted for retained post-validation failures.",
        )

    def _validate_batch(self, files: list[UploadFile] | None) -> None:
        if not files:
            raise UnsupportedFileTypeError("At least one file is required.")
        if len(files) > self.settings.max_batch_files:
            raise BatchTooLargeError()

    async def _process_upload_item(
        self,
        upload: UploadFile,
        item_id: UUID,
        *,
        source_type: str | None,
    ) -> None:
        item = self.session.get(IngestionItem, item_id)
        if item is None:
            return
        temp_path: Path | None = None
        expected: FilenameValidationResult | None = None
        try:
            expected = self.validation_service.validate_filename(upload.filename)
            item.original_filename = expected.original_filename
            item.status = IngestionItemStatus.VALIDATING.value
            item.started_at = self._now()
            item.attempt_count = (item.attempt_count or 0) + 1
            self.session.commit()

            temp_path, sha256, actual_size, header = await self._stream_to_temp(upload, item.id)
            detected = self.validation_service.validate_content(
                temp_path=str(temp_path),
                header=header,
                size_bytes=actual_size,
                expected=expected,
            )
            scan_result = await self.scanner.scan(temp_path)

            item = self.session.get(IngestionItem, item_id)
            if item is None:
                return
            item.sha256 = sha256
            item.actual_size_bytes = actual_size
            item.detected_file_type = detected.file_type
            item.detected_mime_type = detected.mime_type
            item.scanner_status = scan_result.status
            item.scanner_message = scan_result.message
            self.session.commit()

            duplicate = self.document_repository.get_by_sha256(sha256)
            if duplicate is not None:
                self.item_repository.mark_duplicate(item, duplicate.id)
                item.completed_at = self._now()
                self.session.commit()
                return

            await self._register_unique_document(
                item=item,
                temp_path=temp_path,
                expected=expected,
                source_type=source_type,
            )
            temp_path = None
        except IngestionError as exc:
            await self._mark_item_failed(
                item_id,
                exc,
                temp_path=temp_path,
                expected=expected,
                source_type=source_type,
            )
        except SQLAlchemyError as exc:
            await self._mark_item_failed(
                item_id,
                DatabaseRegistrationError(),
                temp_path=temp_path,
                expected=expected,
                source_type=source_type,
            )
            _ = exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            upload.file.close()

    async def _stream_to_temp(
        self, upload: UploadFile, item_id: UUID
    ) -> tuple[Path, str, int, bytes]:
        self.settings.upload_temp_path.mkdir(parents=True, exist_ok=True, mode=0o750)
        temp_path = self.settings.upload_temp_path / f"{item_id}-{uuid4()}.upload"
        digest = hashlib.sha256()
        size = 0
        header = bytearray()

        try:
            with temp_path.open("xb") as output:
                while True:
                    chunk = upload.file.read(STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > self.settings.max_upload_bytes:
                        raise FileTooLargeError()
                    digest.update(chunk)
                    if len(header) < HEADER_BYTES:
                        header.extend(chunk[: HEADER_BYTES - len(header)])
                    output.write(chunk)
        except IngestionError:
            temp_path.unlink(missing_ok=True)
            raise
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            raise StorageOperationError() from exc

        if size == 0:
            temp_path.unlink(missing_ok=True)
            raise EmptyFileError()
        return temp_path, digest.hexdigest(), size, bytes(header)

    async def _register_unique_document(
        self,
        *,
        item: IngestionItem,
        temp_path: Path,
        expected: FilenameValidationResult,
        source_type: str | None,
    ) -> None:
        document_id = uuid4()
        storage_key = self.storage_service.make_storage_key(
            document_id=document_id,
            extension=expected.extension,
        )
        document = Document(
            id=document_id,
            document_code=f"DOC-{document_id.hex[:12].upper()}",
            original_filename=expected.original_filename,
            stored_filename=storage_key,
            file_type=item.detected_file_type,
            mime_type=item.detected_mime_type,
            source_type=source_type,
            sha256=item.sha256,
            file_size_bytes=item.actual_size_bytes,
            parse_status=ParseStatus.REGISTERED.value,
        )
        self.document_repository.create(document)
        item_id = item.id
        try:
            self.session.flush()
            await self.storage_service.finalize(temp_path=temp_path, storage_key=storage_key)
            item.document_id = document.id
            item.status = IngestionItemStatus.STORED.value
            item.completed_at = self._now()
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            duplicate = self.document_repository.get_by_sha256(item.sha256 or "")
            if duplicate is not None:
                duplicate_item = self.session.get(IngestionItem, item_id)
                if duplicate_item is not None:
                    self.item_repository.mark_duplicate(duplicate_item, duplicate.id)
                    duplicate_item.completed_at = self._now()
                    self.session.commit()
                temp_path.unlink(missing_ok=True)
                return
            await self._quarantine_item(
                item_id,
                temp_path=temp_path,
                expected=expected,
                source_type=source_type,
                failure=DatabaseRegistrationError(),
            )
        except IngestionError:
            self.session.rollback()
            await self._quarantine_item(
                item.id,
                temp_path=temp_path,
                expected=expected,
                source_type=source_type,
                failure=StorageOperationError(),
            )

    async def _quarantine_item(
        self,
        item_id: UUID,
        *,
        temp_path: Path,
        expected: FilenameValidationResult,
        source_type: str | None,
        failure: IngestionError,
    ) -> None:
        item = self.session.get(IngestionItem, item_id)
        if item is None:
            temp_path.unlink(missing_ok=True)
            return
        quarantine_key = f".quarantine/{item.id}/{uuid4()}{expected.extension}"
        try:
            await self.storage_service.finalize(temp_path=temp_path, storage_key=quarantine_key)
            metadata = dict(item.metadata_json)
            metadata.update(
                {
                    "quarantine_storage_key": quarantine_key,
                    "extension": expected.extension,
                    "source_type": source_type,
                }
            )
            item.metadata_json = metadata
        except IngestionError:
            temp_path.unlink(missing_ok=True)
        self.item_repository.mark_failed(
            item,
            error_code=failure.code,
            error_message=failure.safe_message,
        )
        item.completed_at = self._now()
        self.session.commit()

    async def _mark_item_failed(
        self,
        item_id: UUID,
        failure: IngestionError,
        *,
        temp_path: Path | None,
        expected: FilenameValidationResult | None,
        source_type: str | None,
    ) -> None:
        self.session.rollback()
        if temp_path is not None and expected is not None and failure.retryable:
            await self._quarantine_item(
                item_id,
                temp_path=temp_path,
                expected=expected,
                source_type=source_type,
                failure=failure,
            )
            return
        item = self.session.get(IngestionItem, item_id)
        if item is None:
            return
        self.item_repository.mark_failed(
            item,
            error_code=failure.code,
            error_message=failure.safe_message,
        )
        item.completed_at = self._now()
        self.session.commit()

    async def _retry_quarantined_item(self, item_id: UUID) -> IngestionItem:
        item = self.session.get(IngestionItem, item_id)
        if item is None:
            raise IngestionItemNotRetryableError()
        quarantine_key = item.metadata_json.get("quarantine_storage_key")
        extension = item.metadata_json.get("extension")
        if not isinstance(quarantine_key, str) or not isinstance(extension, str):
            raise IngestionItemNotRetryableError()
        if not isinstance(self.storage_service.backend, LocalStorageBackend):
            raise IngestionItemNotRetryableError()

        item.status = IngestionItemStatus.VALIDATING.value
        item.error_code = None
        item.error_message = None
        item.started_at = self._now()
        item.completed_at = None
        item.attempt_count = (item.attempt_count or 0) + 1
        self.session.commit()

        source_path = self.storage_service.backend.resolve_key(quarantine_key)
        expected = FilenameValidationResult(
            original_filename=item.original_filename,
            extension=extension,
            expected_file_type=item.detected_file_type or extension.removeprefix("."),
            expected_mime_type=item.detected_mime_type or "application/octet-stream",
        )
        await self._register_unique_document(
            item=item,
            temp_path=source_path,
            expected=expected,
            source_type=str(item.metadata_json.get("source_type") or "") or None,
        )
        item = self.session.get(IngestionItem, item_id)
        if item is None:
            raise IngestionItemNotRetryableError()
        return item

    def _complete_job(self, job_id: UUID) -> IngestionJob:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise IngestionJobNotFoundError()
        items = self.job_repository.list_items_for_job(job.id)
        processed = sum(
            1
            for item in items
            if item.status
            in {IngestionItemStatus.STORED.value, IngestionItemStatus.DUPLICATE.value}
        )
        failed = sum(1 for item in items if item.status == IngestionItemStatus.FAILED.value)
        job.failed_files = failed
        job.processed_files = processed
        if failed == 0:
            job.status = JobStatus.COMPLETED.value
            job.error_message = None
        elif processed == 0:
            job.status = JobStatus.FAILED.value
            job.error_message = "All files failed ingestion."
        else:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value
            job.error_message = "Some files failed ingestion."
        job.completed_at = self._now()
        self.session.commit()
        return job

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
