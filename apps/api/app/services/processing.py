from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.documents import Chunk, Document, DocumentBlock, DocumentPage, DocumentProcessingRun
from app.models.enums import ParseStatus
from app.repositories.documents import DocumentRepository
from app.repositories.processing import (
    ChunkRepository,
    DocumentBlockRepository,
    DocumentPageRepository,
    ProcessingRunRepository,
)
from app.schemas.documents import (
    ChunkListResponse,
    ChunkRead,
    DocumentBlockRead,
    DocumentPageListItem,
    DocumentPageRead,
    DocumentProcessingRunRead,
    DocumentProcessingStatusRead,
    DocumentRead,
    ProcessingResponse,
)
from app.services.chunking import ChunkingService
from app.services.ingestion_errors import DocumentNotFoundError
from app.services.parsers import ParserRegistry
from app.services.parsing_contracts import ParseContext, ParsedDocumentData, ParserWarning
from app.services.processing_errors import (
    DocumentAlreadyProcessingError,
    DocumentProcessingError,
    PageRenderError,
    ProcessingRetryNotAllowedError,
    StoredDocumentMissingError,
)
from app.services.storage import (
    DocumentStorageService,
    LocalStorageBackend,
    RenderedPageStorageService,
)


class DocumentProcessingService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings,
        document_storage: DocumentStorageService | None = None,
        rendered_storage: RenderedPageStorageService | None = None,
        parser_registry: ParserRegistry | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.documents = DocumentRepository(session)
        self.pages = DocumentPageRepository(session)
        self.blocks = DocumentBlockRepository(session)
        self.chunks = ChunkRepository(session)
        self.runs = ProcessingRunRepository(session)
        self.document_storage = document_storage or DocumentStorageService(
            LocalStorageBackend(settings.upload_root_path)
        )
        self.rendered_storage = rendered_storage or RenderedPageStorageService(
            LocalStorageBackend(settings.rendered_pages_root_path)
        )
        self.parser_registry = parser_registry or ParserRegistry()
        self.chunking = ChunkingService(settings)

    def process_document(self, document_id: UUID, *, force: bool = False) -> ProcessingResponse:
        document = self._get_document(document_id)
        if document.parse_status == ParseStatus.PROCESSING.value:
            raise DocumentAlreadyProcessingError()
        if (
            document.parse_status
            in {
                ParseStatus.COMPLETED.value,
                ParseStatus.COMPLETED_WITH_WARNINGS.value,
            }
            and not force
        ):
            return self._status_response(document)

        run = self._start_run(document)
        started_at = run.started_at or self._now()

        try:
            source_path = self._stored_document_path(document)
            parser = self.parser_registry.get_parser(document.file_type, document.mime_type)
            parsed = parser.parse(
                context=self._parse_context(document=document, source_path=source_path)
            )
            block_count, chunk_count = self._replace_artifacts(document, parsed)
            self._complete_run(document, run, parsed, started_at, block_count, chunk_count)
            self.session.commit()
        except DocumentProcessingError as exc:
            self._mark_failed(
                document_id=document.id, run_id=run.id, failure=exc, started_at=started_at
            )
            raise
        except Exception as exc:
            failure = DocumentProcessingError()
            self._mark_failed(
                document_id=document.id, run_id=run.id, failure=failure, started_at=started_at
            )
            raise failure from exc

        return self._status_response(document)

    def retry_document(self, document_id: UUID, *, force: bool = False) -> ProcessingResponse:
        document = self._get_document(document_id)
        if document.parse_status != ParseStatus.FAILED.value and not force:
            raise ProcessingRetryNotAllowedError()
        return self.process_document(document_id, force=True)

    def get_status(self, document_id: UUID) -> DocumentProcessingStatusRead:
        document = self._get_document(document_id)
        return self._status_response(document).status

    def list_runs(self, document_id: UUID) -> list[DocumentProcessingRunRead]:
        self._get_document(document_id)
        return [
            DocumentProcessingRunRead.model_validate(run)
            for run in self.runs.list_for_document(document_id)
        ]

    def list_pages(self, document_id: UUID) -> list[DocumentPageListItem]:
        self._get_document(document_id)
        return [self._page_list_item(page) for page in self.pages.list_for_document(document_id)]

    def get_page(self, document_id: UUID, page_number: int) -> DocumentPageRead:
        self._get_document(document_id)
        page = self.pages.get_by_number(document_id, page_number)
        if page is None:
            raise DocumentNotFoundError("Document page was not found.")
        blocks = self.blocks.list_for_page(page.id)
        return DocumentPageRead(
            **self._page_list_item(page).model_dump(),
            blocks=[DocumentBlockRead.model_validate(block) for block in blocks],
        )

    def get_page_image_path(self, document_id: UUID, page_number: int) -> Path:
        self._get_document(document_id)
        page = self.pages.get_by_number(document_id, page_number)
        if page is None or not page.rendered_image_path:
            raise DocumentNotFoundError("Rendered page image was not found.")
        backend = self.rendered_storage.backend
        if not isinstance(backend, LocalStorageBackend):
            raise PageRenderError("Only local rendered page storage is supported in Phase 4.")
        path = backend.resolve_key(page.rendered_image_path)
        if not path.is_file():
            raise DocumentNotFoundError("Rendered page image was not found.")
        return path

    def list_chunks(
        self,
        document_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        chunk_kind: str | None = None,
    ) -> ChunkListResponse:
        self._get_document(document_id)
        items, total = self.chunks.list_for_document(
            document_id,
            page=page,
            page_size=page_size,
            chunk_kind=chunk_kind,
        )
        return ChunkListResponse(
            items=[ChunkRead.model_validate(chunk) for chunk in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_chunk(self, document_id: UUID, chunk_id: UUID) -> ChunkRead:
        self._get_document(document_id)
        chunk = self.chunks.get_by_id(document_id, chunk_id)
        if chunk is None:
            raise DocumentNotFoundError("Document chunk was not found.")
        return ChunkRead.model_validate(chunk)

    def _get_document(self, document_id: UUID) -> Document:
        document = self.documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        return document

    def _start_run(self, document: Document) -> DocumentProcessingRun:
        now = self._now()
        run = self.runs.create(
            DocumentProcessingRun(
                document_id=document.id,
                status=ParseStatus.PROCESSING.value,
                started_at=now,
            )
        )
        document.parse_status = ParseStatus.PROCESSING.value
        document.parsing_started_at = now
        document.parsing_completed_at = None
        self.session.commit()
        self.session.refresh(run)
        self.session.refresh(document)
        return run

    def _replace_artifacts(self, document: Document, parsed: ParsedDocumentData) -> tuple[int, int]:
        self._delete_rendered_pages(document.id)
        self.chunks.delete_for_document(document.id)
        self.blocks.delete_for_document(document.id)
        self.pages.delete_for_document(document.id)
        self.session.flush()

        page_by_number: dict[int, DocumentPage] = {}
        created_blocks: list[DocumentBlock] = []
        for parsed_page in parsed.pages:
            page = self.pages.create(
                DocumentPage(
                    document_id=document.id,
                    page_number=parsed_page.page_number,
                    text_content=parsed_page.text,
                    rendered_image_path=parsed_page.rendered_image_key,
                    logical_page_key=parsed_page.logical_page_key,
                    width=parsed_page.width,
                    height=parsed_page.height,
                    ocr_used=parsed_page.ocr_used,
                    ocr_confidence=parsed_page.ocr_confidence,
                    warnings_json=[warning.as_dict() for warning in parsed_page.warnings],
                    parser_metadata_json=parsed_page.parser_metadata,
                    metadata_json=parsed_page.metadata,
                )
            )
            page_by_number[parsed_page.page_number] = page
        self.session.flush()

        for parsed_page in parsed.pages:
            page = page_by_number[parsed_page.page_number]
            for parsed_block in parsed_page.blocks:
                created_blocks.append(
                    self.blocks.create(
                        DocumentBlock(
                            document_id=document.id,
                            document_page_id=page.id,
                            block_index=parsed_block.block_index,
                            block_type=parsed_block.block_type.value,
                            section_path=parsed_block.section_path,
                            heading_level=parsed_block.heading_level,
                            text_content=parsed_block.text,
                            bounding_box_json=parsed_block.bounding_box,
                            table_metadata_json=parsed_block.table_metadata,
                            parser_metadata_json=parsed_block.parser_metadata,
                            metadata_json=parsed_block.metadata,
                        )
                    )
                )
        self.session.flush()

        chunk_data = self.chunking.build_chunks(document, created_blocks)
        for chunk in chunk_data:
            self.chunks.create(
                Chunk(
                    document_id=document.id,
                    document_page_id=chunk.document_page_id,
                    chunk_index=chunk.chunk_index,
                    chunk_kind=chunk.chunk_kind.value,
                    first_page_number=chunk.first_page_number,
                    last_page_number=chunk.last_page_number,
                    section_path=chunk.section_path,
                    text_content=chunk.text,
                    token_count=chunk.token_count,
                    citation_label=chunk.citation_label,
                    source_block_ids_json=[str(block_id) for block_id in chunk.source_block_ids],
                    equipment_hint=chunk.equipment_hint,
                    parser_metadata_json=chunk.parser_metadata,
                )
            )
        self.session.flush()
        return len(created_blocks), len(chunk_data)

    def _complete_run(
        self,
        document: Document,
        run: DocumentProcessingRun,
        parsed: ParsedDocumentData,
        started_at: datetime,
        block_count: int,
        chunk_count: int,
    ) -> None:
        completed_at = self._now()
        duration_ms = _duration_ms(started_at, completed_at)
        warnings = self._warnings(parsed)
        status = (
            ParseStatus.COMPLETED_WITH_WARNINGS.value if warnings else ParseStatus.COMPLETED.value
        )
        document.parse_status = status
        document.parser_name = parsed.parser_name
        document.parser_version = parsed.parser_version
        document.page_count = parsed.page_count
        document.parse_warnings_json = warnings
        document.parsing_completed_at = completed_at
        document.processing_duration_ms = duration_ms
        document.ocr_used = parsed.ocr_used
        document.normalized_metadata_json = parsed.metadata

        run.status = status
        run.parser_name = parsed.parser_name
        run.parser_version = parsed.parser_version
        run.fallback_parser_name = parsed.fallback_parser_name
        run.ocr_used = parsed.ocr_used
        run.completed_at = completed_at
        run.duration_ms = duration_ms
        run.page_count = parsed.page_count
        run.block_count = block_count
        run.chunk_count = chunk_count
        run.warning_count = len(warnings)
        run.warnings_json = warnings
        run.metadata_json = parsed.metadata

    def _mark_failed(
        self,
        *,
        document_id: UUID,
        run_id: UUID,
        failure: DocumentProcessingError,
        started_at: datetime,
    ) -> None:
        self.session.rollback()
        document = self.documents.get_by_id(document_id)
        run = self.session.get(DocumentProcessingRun, run_id)
        if document is None or run is None:
            return
        completed_at = self._now()
        document.parse_status = ParseStatus.FAILED.value
        document.parsing_completed_at = completed_at
        document.processing_duration_ms = _duration_ms(started_at, completed_at)
        document.parse_warnings_json = []
        run.status = ParseStatus.FAILED.value
        run.completed_at = completed_at
        run.duration_ms = document.processing_duration_ms
        run.error_code = failure.code
        run.error_message = failure.safe_message
        run.metadata_json = {"details": failure.details}
        self.session.commit()

    def _status_response(self, document: Document) -> ProcessingResponse:
        latest_run = self.runs.latest_for_document(document.id)
        status = DocumentProcessingStatusRead(
            document=DocumentRead.model_validate(document),
            latest_run=DocumentProcessingRunRead.model_validate(latest_run) if latest_run else None,
            page_count=document.page_count or 0,
            block_count=len(document.blocks),
            chunk_count=len(document.chunks),
        )
        return ProcessingResponse(status=status)

    def _stored_document_path(self, document: Document) -> Path:
        if not document.stored_filename:
            raise StoredDocumentMissingError()
        backend = self.document_storage.backend
        if not isinstance(backend, LocalStorageBackend):
            raise StoredDocumentMissingError()
        path = backend.resolve_key(document.stored_filename)
        if not path.is_file():
            raise StoredDocumentMissingError()
        return path

    def _parse_context(self, *, document: Document, source_path: Path) -> ParseContext:
        return ParseContext(
            document_id=document.id,
            document_code=document.document_code,
            file_path=source_path,
            file_type=document.file_type,
            mime_type=document.mime_type,
            source_type=document.source_type,
            settings=self.settings,
            rendered_storage=self.rendered_storage,
        )

    def _delete_rendered_pages(self, document_id: UUID) -> None:
        backend = self.rendered_storage.backend
        if not isinstance(backend, LocalStorageBackend):
            return
        for page in self.pages.list_for_document(document_id):
            if not page.rendered_image_path:
                continue
            backend.resolve_key(page.rendered_image_path).unlink(missing_ok=True)

    def _page_list_item(self, page: DocumentPage) -> DocumentPageListItem:
        return DocumentPageListItem(
            id=page.id,
            document_id=page.document_id,
            page_number=page.page_number,
            logical_page_key=page.logical_page_key,
            text_content=page.text_content,
            has_rendered_image=bool(page.rendered_image_path),
            image_url=f"/api/v1/documents/{page.document_id}/pages/{page.page_number}/image"
            if page.rendered_image_path
            else None,
            width=page.width,
            height=page.height,
            ocr_used=page.ocr_used,
            ocr_confidence=page.ocr_confidence,
            warnings_json=page.warnings_json,
            parser_metadata_json=page.parser_metadata_json,
            metadata_json=page.metadata_json,
            created_at=page.created_at,
            updated_at=page.updated_at,
        )

    def _warnings(self, parsed: ParsedDocumentData) -> list[dict[str, str | int | None]]:
        warnings: list[ParserWarning] = [*parsed.warnings]
        for page in parsed.pages:
            warnings.extend(page.warnings)
        deduped: list[dict[str, str | int | None]] = []
        seen: set[tuple[str, str, int | None]] = set()
        for warning in warnings:
            key = (warning.code, warning.scope, warning.page_number)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(warning.as_dict())
        return deduped

    def _now(self) -> datetime:
        return datetime.now(UTC)


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=UTC)
    return max(0, int((completed_at - started_at).total_seconds() * 1000))
