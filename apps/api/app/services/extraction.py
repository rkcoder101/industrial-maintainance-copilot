import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.assets import Equipment, EquipmentAlias
from app.models.documents import Chunk, Document
from app.models.enums import (
    ActionStatus,
    ChunkExtractionStatus,
    EventStatus,
    EventType,
    ExtractionFactStatus,
    ExtractionFactType,
    JobStatus,
    MeasurementQuality,
    ParseStatus,
    ProcedureStatus,
    Severity,
    WorkOrderPriority,
    WorkOrderStatus,
)
from app.models.events import Event, FailureEvent, Measurement
from app.models.jobs import ChunkExtractionRun, ExtractedFact, ExtractionRun
from app.models.maintenance import MaintenanceAction, Procedure, WorkOrder
from app.repositories.documents import DocumentRepository
from app.repositories.extraction import (
    ChunkExtractionRunRepository,
    EquipmentAliasRepository,
    ExtractedFactRepository,
    ExtractionRunRepository,
)
from app.repositories.processing import ChunkRepository
from app.schemas.extraction import (
    DocumentExtractionStatusRead,
    ExtractedFactListResponse,
    ExtractedFactRead,
    ExtractionResponse,
    ExtractionRunRead,
)
from app.services.extraction_candidates import CandidateSpottingService
from app.services.extraction_contracts import ExtractionCandidate, ExtractionRequest, ProviderFact
from app.services.extraction_errors import (
    ExtractedFactNotFoundError,
    ExtractionAlreadyProcessingError,
    ExtractionDisabledError,
    ExtractionError,
    ExtractionNotReadyError,
    ExtractionProviderError,
    ExtractionRetryNotAllowedError,
    ExtractionRunNotFoundError,
)
from app.services.extraction_providers import ExtractionProvider, build_extraction_provider
from app.services.ingestion_errors import DocumentNotFoundError

EXTRACTOR_NAME = "structured_extraction"
EXTRACTOR_VERSION = "phase-05"
CANONICAL_FACT_TYPES = {
    ExtractionFactType.EVENT.value,
    ExtractionFactType.FAILURE_EVENT.value,
    ExtractionFactType.MEASUREMENT.value,
    ExtractionFactType.MAINTENANCE_ACTION.value,
    ExtractionFactType.WORK_ORDER.value,
    ExtractionFactType.PROCEDURE.value,
}


class DocumentExtractionService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings,
        provider: ExtractionProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.documents = DocumentRepository(session)
        self.chunks = ChunkRepository(session)
        self.runs = ExtractionRunRepository(session)
        self.chunk_runs = ChunkExtractionRunRepository(session)
        self.facts = ExtractedFactRepository(session)
        self.aliases = EquipmentAliasRepository(session)
        self.candidates = CandidateSpottingService()
        self.provider = provider or build_extraction_provider(settings)

    def extract_document(self, document_id: UUID, *, force: bool = False) -> ExtractionResponse:
        if not self.settings.extraction_enabled:
            raise ExtractionDisabledError()
        document = self._get_ready_document(document_id)
        latest = self.runs.latest_for_document(document.id)
        if latest and latest.status == JobStatus.PROCESSING.value:
            raise ExtractionAlreadyProcessingError()
        if latest and latest.status == JobStatus.COMPLETED.value and not force:
            return self._status_response(document)

        run = self._start_run(document, force=force)
        started_at = run.started_at or self._now()
        try:
            self._execute_run(document, run, started_at)
            self.session.commit()
        except ExtractionError as exc:
            self._mark_failed(run.id, exc, started_at)
            raise
        except Exception as exc:
            failure = ExtractionError()
            self._mark_failed(run.id, failure, started_at)
            raise failure from exc
        return self._status_response(document)

    def retry_document(self, document_id: UUID, *, force: bool = False) -> ExtractionResponse:
        document = self._get_ready_document(document_id)
        latest = self.runs.latest_for_document(document.id)
        retryable = latest is not None and latest.status in {
            JobStatus.FAILED.value,
            JobStatus.COMPLETED_WITH_ERRORS.value,
        }
        if not retryable and not force:
            raise ExtractionRetryNotAllowedError()
        return self.extract_document(document_id, force=True)

    def get_status(self, document_id: UUID) -> DocumentExtractionStatusRead:
        document = self._get_document(document_id)
        return self._status_response(document).status

    def list_runs(self, document_id: UUID) -> list[ExtractionRunRead]:
        self._get_document(document_id)
        return [
            ExtractionRunRead.model_validate(run)
            for run in self.runs.list_for_document(document_id)
        ]

    def get_run(self, run_id: UUID) -> ExtractionRunRead:
        run = self.runs.get_by_id(run_id)
        if run is None:
            raise ExtractionRunNotFoundError()
        return ExtractionRunRead.model_validate(run)

    def list_facts_for_run(
        self,
        run_id: UUID,
        *,
        page: int = 1,
        page_size: int = 100,
        status: str | None = None,
        fact_type: str | None = None,
    ) -> ExtractedFactListResponse:
        if self.runs.get_by_id(run_id) is None:
            raise ExtractionRunNotFoundError()
        items, total = self.facts.list_for_run(
            run_id,
            page=page,
            page_size=page_size,
            status=status,
            fact_type=fact_type,
        )
        return ExtractedFactListResponse(
            items=[ExtractedFactRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_fact(self, fact_id: UUID) -> ExtractedFactRead:
        fact = self.facts.get_by_id(fact_id)
        if fact is None:
            raise ExtractedFactNotFoundError()
        return ExtractedFactRead.model_validate(fact)

    def _execute_run(
        self,
        document: Document,
        run: ExtractionRun,
        started_at: datetime,
    ) -> None:
        chunks, total_chunks = self.chunks.list_for_document(document.id, page=1, page_size=10000)
        equipment = list(self.session.scalars(select(Equipment).order_by(Equipment.equipment_tag)))
        run.total_chunk_count = total_chunks

        for chunk in chunks:
            candidate = self.candidates.build_candidate(chunk, equipment)
            if not candidate.eligible:
                self._record_skipped_chunk(run, document, chunk, candidate.model_dump(mode="json"))
                continue
            run.eligible_chunk_count += 1
            self._extract_chunk(document, run, chunk, candidate.model_dump(mode="json"), equipment)

        completed_at = self._now()
        run.completed_at = completed_at
        run.duration_ms = _duration_ms(started_at, completed_at)
        run.warning_count = len(run.warnings_json)
        run.status = (
            JobStatus.COMPLETED_WITH_ERRORS.value
            if run.failed_chunk_count or run.rejected_fact_count
            else JobStatus.COMPLETED.value
        )
        run.metadata_json = {
            **run.metadata_json,
            "idempotency": "canonical writes use deterministic codes and duplicate lookup",
            "qdrant_indexed": False,
        }

    def _extract_chunk(
        self,
        document: Document,
        run: ExtractionRun,
        chunk: Chunk,
        candidate_summary: dict[str, Any],
        equipment: list[Equipment],
    ) -> None:
        started_at = self._now()
        chunk_run = self.chunk_runs.create(
            ChunkExtractionRun(
                extraction_run_id=run.id,
                document_id=document.id,
                chunk_id=chunk.id,
                status=ChunkExtractionStatus.PROCESSING.value,
                provider_name=self.provider.name,
                model_name=self.provider.model_name,
                prompt_version=self.settings.extraction_prompt_version,
                started_at=started_at,
                candidate_summary_json=candidate_summary,
                input_excerpt=_truncate(chunk.text_content or "", 1200),
            )
        )
        self.session.flush()
        request = ExtractionRequest(
            document_id=document.id,
            document_code=document.document_code,
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            citation_label=chunk.citation_label,
            first_page_number=chunk.first_page_number,
            last_page_number=chunk.last_page_number,
            section_path=chunk.section_path,
            text=_truncate(chunk.text_content or "", self.settings.extraction_max_chunk_characters),
            candidates=ExtractionCandidate.model_validate(candidate_summary),
            prompt_version=self.settings.extraction_prompt_version,
        )

        try:
            response = self.provider.extract(request)
            chunk_run.response_json = response.model_dump(mode="json")
            chunk_run.warnings_json = response.warnings
            for provider_fact in response.facts:
                status = self._persist_fact(
                    document, run, chunk_run, chunk, provider_fact, equipment
                )
                chunk_run.fact_count += 1
                run.fact_count += 1
                if status == ExtractionFactStatus.ACCEPTED.value:
                    chunk_run.accepted_fact_count += 1
                    run.accepted_fact_count += 1
                elif status == ExtractionFactStatus.DUPLICATE.value:
                    chunk_run.duplicate_fact_count += 1
                    run.duplicate_fact_count += 1
                elif status == ExtractionFactStatus.REJECTED.value:
                    chunk_run.rejected_fact_count += 1
                    run.rejected_fact_count += 1
            chunk_run.status = ChunkExtractionStatus.COMPLETED.value
            run.processed_chunk_count += 1
        except (ExtractionProviderError, ValidationError) as exc:
            chunk_run.status = ChunkExtractionStatus.FAILED.value
            chunk_run.error_code = "provider_validation_failed"
            chunk_run.error_message = "Provider response could not be validated safely."
            chunk_run.validation_errors_json = _validation_errors(exc)
            run.failed_chunk_count += 1
        finally:
            completed_at = self._now()
            chunk_run.completed_at = completed_at
            chunk_run.duration_ms = _duration_ms(started_at, completed_at)

    def _persist_fact(
        self,
        document: Document,
        run: ExtractionRun,
        chunk_run: ChunkExtractionRun,
        chunk: Chunk,
        provider_fact: ProviderFact,
        equipment: list[Equipment],
    ) -> str:
        normalized = provider_fact.model_dump(mode="json")
        equipment_obj = self._resolve_equipment(provider_fact, equipment)
        fingerprint = _fingerprint(document.id, chunk.id, normalized)
        status, reason = self._initial_status(provider_fact, equipment_obj)
        canonical_type: str | None = None
        canonical_id: UUID | None = None

        if status == ExtractionFactStatus.ACCEPTED.value:
            canonical_type, canonical_id, is_duplicate = self._persist_canonical(
                document,
                chunk,
                provider_fact,
                equipment_obj,
                fingerprint,
            )
            if is_duplicate:
                status = ExtractionFactStatus.DUPLICATE.value
        elif (
            status == ExtractionFactStatus.STAGED.value
            and provider_fact.fact_type in CANONICAL_FACT_TYPES
        ):
            reason = "confidence_below_auto_accept_threshold"

        extracted = self.facts.create(
            ExtractedFact(
                extraction_run_id=run.id,
                chunk_extraction_run_id=chunk_run.id,
                document_id=document.id,
                source_page_id=chunk.document_page_id,
                source_chunk_id=chunk.id,
                equipment_id=equipment_obj.id if equipment_obj else None,
                fact_type=provider_fact.fact_type,
                status=status,
                fingerprint=fingerprint,
                confidence=provider_fact.confidence,
                evidence_span=provider_fact.evidence.text,
                source_text=provider_fact.evidence.text,
                raw_payload_json=provider_fact.model_dump(mode="json"),
                normalized_payload_json=normalized,
                rejection_reason=reason,
                canonical_type=canonical_type,
                canonical_id=canonical_id,
                extractor_version=EXTRACTOR_VERSION,
                prompt_version=self.settings.extraction_prompt_version,
                accepted_at=self._now()
                if status
                in {ExtractionFactStatus.ACCEPTED.value, ExtractionFactStatus.DUPLICATE.value}
                else None,
                metadata_json={"citation_label": chunk.citation_label},
            )
        )
        self.session.flush()
        return extracted.status

    def _initial_status(
        self,
        fact: ProviderFact,
        equipment: Equipment | None,
    ) -> tuple[str, str | None]:
        if fact.confidence < self.settings.extraction_min_confidence:
            return ExtractionFactStatus.REJECTED.value, "confidence_below_minimum"
        if fact.fact_type == ExtractionFactType.EQUIPMENT_MENTION.value and equipment is None:
            return ExtractionFactStatus.REJECTED.value, "equipment_unresolved"
        if fact.fact_type in CANONICAL_FACT_TYPES and equipment is None:
            return ExtractionFactStatus.REJECTED.value, "equipment_unresolved"
        if fact.fact_type == ExtractionFactType.MEASUREMENT.value and (
            fact.metric_name is None or fact.metric_value is None
        ):
            return ExtractionFactStatus.REJECTED.value, "measurement_missing_metric"
        if fact.fact_type == ExtractionFactType.WORK_ORDER.value and not (
            fact.work_order_number or fact.title or fact.summary
        ):
            return ExtractionFactStatus.REJECTED.value, "work_order_missing_identifier"
        if fact.fact_type == ExtractionFactType.PROCEDURE.value and not (
            fact.procedure_code or fact.title or fact.summary
        ):
            return ExtractionFactStatus.REJECTED.value, "procedure_missing_identifier"
        if fact.fact_type == ExtractionFactType.COMPLIANCE_CANDIDATE.value:
            return ExtractionFactStatus.STAGED.value, "compliance_candidates_are_review_only"
        if fact.fact_type == ExtractionFactType.RELATIONSHIP.value:
            return ExtractionFactStatus.STAGED.value, "relationships_are_review_only_in_phase_5"
        if fact.confidence < self.settings.extraction_auto_accept_confidence:
            return ExtractionFactStatus.STAGED.value, None
        return ExtractionFactStatus.ACCEPTED.value, None

    def _persist_canonical(
        self,
        document: Document,
        chunk: Chunk,
        fact: ProviderFact,
        equipment: Equipment | None,
        fingerprint: str,
    ) -> tuple[str | None, UUID | None, bool]:
        if fact.fact_type == ExtractionFactType.EQUIPMENT_MENTION.value and equipment:
            alias = (fact.alias or fact.equipment_tag or equipment.equipment_tag).strip()
            existing_alias = self.aliases.get(equipment.id, alias)
            if existing_alias is None:
                existing_alias = self.aliases.create(
                    EquipmentAlias(
                        equipment_id=equipment.id,
                        alias=alias,
                        alias_type="extracted",
                        source_document_id=document.id,
                        source_page_id=chunk.document_page_id,
                        source_chunk_id=chunk.id,
                        evidence_span=fact.evidence.text,
                        confidence=fact.confidence,
                        extractor_version=EXTRACTOR_VERSION,
                        extracted_at=self._now(),
                    )
                )
                self.session.flush()
                return "equipment_alias", existing_alias.id, False
            return "equipment_alias", existing_alias.id, True
        if fact.fact_type == ExtractionFactType.WORK_ORDER.value and equipment:
            return self._persist_work_order(document, chunk, fact, equipment, fingerprint)
        if fact.fact_type == ExtractionFactType.PROCEDURE.value:
            return self._persist_procedure(document, chunk, fact, fingerprint)
        if fact.fact_type == ExtractionFactType.MEASUREMENT.value and equipment:
            return self._persist_measurement(document, chunk, fact, equipment)
        if fact.fact_type == ExtractionFactType.MAINTENANCE_ACTION.value and equipment:
            return self._persist_action(document, chunk, fact, equipment)
        if (
            fact.fact_type
            in {ExtractionFactType.EVENT.value, ExtractionFactType.FAILURE_EVENT.value}
            and equipment
        ):
            event, event_duplicate = self._get_or_create_event(
                document, chunk, fact, equipment, fingerprint
            )
            if fact.fact_type == ExtractionFactType.FAILURE_EVENT.value:
                existing_failure = self.session.scalar(
                    select(FailureEvent).where(FailureEvent.event_id == event.id)
                )
                if existing_failure is None:
                    existing_failure = FailureEvent(
                        event_id=event.id,
                        failure_mode=fact.failure_mode or fact.summary or "equipment failure",
                        failure_mechanism=fact.failure_mechanism,
                        symptoms_json=fact.symptoms,
                    )
                    self.session.add(existing_failure)
                    self.session.flush()
                    return "failure_event", existing_failure.id, False
                return "failure_event", existing_failure.id, True
            return "event", event.id, event_duplicate
        return None, None, False

    def _persist_work_order(
        self,
        document: Document,
        chunk: Chunk,
        fact: ProviderFact,
        equipment: Equipment,
        fingerprint: str,
    ) -> tuple[str, UUID, bool]:
        number = fact.work_order_number or f"EXT-WO-{fingerprint[:12].upper()}"
        existing = self.session.scalar(
            select(WorkOrder).where(WorkOrder.work_order_number == number)
        )
        if existing is not None:
            return "work_order", existing.id, True
        work_order = WorkOrder(
            work_order_number=number,
            equipment_id=equipment.id,
            title=fact.title or fact.summary or "Extracted work order",
            description=fact.description,
            priority=_work_order_priority(fact.severity),
            status=_work_order_status(fact.status),
            source_document_id=document.id,
            source_page_id=chunk.document_page_id,
            source_chunk_id=chunk.id,
            evidence_span=fact.evidence.text,
            confidence=fact.confidence,
            extractor_version=EXTRACTOR_VERSION,
            extracted_at=self._now(),
            metadata_json={"extraction_fingerprint": fingerprint},
        )
        self.session.add(work_order)
        self.session.flush()
        return "work_order", work_order.id, False

    def _persist_procedure(
        self,
        document: Document,
        chunk: Chunk,
        fact: ProviderFact,
        fingerprint: str,
    ) -> tuple[str, UUID, bool]:
        code = fact.procedure_code or f"EXT-PROC-{fingerprint[:12].upper()}"
        revision = fact.revision or "unknown"
        existing = self.session.scalar(
            select(Procedure).where(
                Procedure.procedure_code == code, Procedure.revision == revision
            )
        )
        if existing is not None:
            return "procedure", existing.id, True
        procedure = Procedure(
            procedure_code=code,
            title=fact.title or fact.summary or "Extracted procedure",
            revision=revision,
            description=fact.description,
            status=_procedure_status(fact.status),
            document_id=document.id,
            source_document_id=document.id,
            source_page_id=chunk.document_page_id,
            source_chunk_id=chunk.id,
            evidence_span=fact.evidence.text,
            confidence=fact.confidence,
            extractor_version=EXTRACTOR_VERSION,
            extracted_at=self._now(),
            metadata_json={"extraction_fingerprint": fingerprint},
        )
        self.session.add(procedure)
        self.session.flush()
        return "procedure", procedure.id, False

    def _persist_measurement(
        self,
        document: Document,
        chunk: Chunk,
        fact: ProviderFact,
        equipment: Equipment,
    ) -> tuple[str, UUID, bool]:
        measured_at = fact.happened_at or self._now()
        existing = self.session.scalar(
            select(Measurement).where(
                Measurement.equipment_id == equipment.id,
                Measurement.source_chunk_id == chunk.id,
                Measurement.metric_name == fact.metric_name,
                Measurement.metric_value == fact.metric_value,
            )
        )
        if existing is not None:
            return "measurement", existing.id, True
        measurement = Measurement(
            equipment_id=equipment.id,
            metric_name=fact.metric_name,
            metric_value=fact.metric_value,
            unit=fact.unit,
            measured_at=measured_at,
            quality=MeasurementQuality.UNKNOWN.value,
            source_document_id=document.id,
            source_page_id=chunk.document_page_id,
            source_chunk_id=chunk.id,
            evidence_span=fact.evidence.text,
            confidence=fact.confidence,
            extractor_version=EXTRACTOR_VERSION,
            extracted_at=self._now(),
        )
        self.session.add(measurement)
        self.session.flush()
        return "measurement", measurement.id, False

    def _persist_action(
        self,
        document: Document,
        chunk: Chunk,
        fact: ProviderFact,
        equipment: Equipment,
    ) -> tuple[str, UUID, bool]:
        description = fact.description or fact.summary or "Extracted maintenance action"
        existing = self.session.scalar(
            select(MaintenanceAction).where(
                MaintenanceAction.equipment_id == equipment.id,
                MaintenanceAction.source_chunk_id == chunk.id,
                MaintenanceAction.description == description,
            )
        )
        if existing is not None:
            return "maintenance_action", existing.id, True
        action = MaintenanceAction(
            equipment_id=equipment.id,
            action_type=fact.action_type,
            description=description,
            performed_at=fact.happened_at,
            status=_action_status(fact.status),
            source_document_id=document.id,
            source_page_id=chunk.document_page_id,
            source_chunk_id=chunk.id,
            evidence_span=fact.evidence.text,
            confidence=fact.confidence,
            extractor_version=EXTRACTOR_VERSION,
            extracted_at=self._now(),
        )
        self.session.add(action)
        self.session.flush()
        return "maintenance_action", action.id, False

    def _get_or_create_event(
        self,
        document: Document,
        chunk: Chunk,
        fact: ProviderFact,
        equipment: Equipment,
        fingerprint: str,
    ) -> tuple[Event, bool]:
        event_code = f"EXT-EVT-{fingerprint[:16].upper()}"
        existing = self.session.scalar(select(Event).where(Event.event_code == event_code))
        if existing is not None:
            return existing, True
        event = Event(
            event_code=event_code,
            equipment_id=equipment.id,
            event_type=_event_type(fact.event_type, fact.fact_type),
            event_time=fact.happened_at,
            severity=_severity(fact.severity),
            summary=fact.summary or fact.failure_mode,
            description=fact.description,
            status=_event_status(fact.status),
            source_document_id=document.id,
            source_page_id=chunk.document_page_id,
            source_chunk_id=chunk.id,
            evidence_span=fact.evidence.text,
            confidence=fact.confidence,
            extractor_version=EXTRACTOR_VERSION,
            extracted_at=self._now(),
            metadata_json={"extraction_fingerprint": fingerprint},
        )
        self.session.add(event)
        self.session.flush()
        return event, False

    def _resolve_equipment(
        self,
        fact: ProviderFact,
        equipment: list[Equipment],
    ) -> Equipment | None:
        if not fact.equipment_tag:
            return None
        normalized = fact.equipment_tag.strip().upper()
        for item in equipment:
            if item.equipment_tag.upper() == normalized:
                return item
        return None

    def _record_skipped_chunk(
        self,
        run: ExtractionRun,
        document: Document,
        chunk: Chunk,
        candidate_summary: dict[str, Any],
    ) -> None:
        self.chunk_runs.create(
            ChunkExtractionRun(
                extraction_run_id=run.id,
                document_id=document.id,
                chunk_id=chunk.id,
                status=ChunkExtractionStatus.SKIPPED.value,
                provider_name=self.provider.name,
                model_name=self.provider.model_name,
                prompt_version=self.settings.extraction_prompt_version,
                candidate_summary_json=candidate_summary,
                input_excerpt=_truncate(chunk.text_content or "", 1200),
                metadata_json={"reason": candidate_summary.get("reason")},
            )
        )
        run.skipped_chunk_count += 1

    def _status_response(self, document: Document) -> ExtractionResponse:
        runs = self.runs.list_for_document(document.id)
        latest_run = runs[0] if runs else None
        fact_count = latest_run.fact_count if latest_run else 0
        accepted = latest_run.accepted_fact_count if latest_run else 0
        return ExtractionResponse(
            status=DocumentExtractionStatusRead(
                document_id=document.id,
                latest_run=ExtractionRunRead.model_validate(latest_run) if latest_run else None,
                total_runs=len(runs),
                fact_count=fact_count,
                accepted_fact_count=accepted,
            )
        )

    def _start_run(self, document: Document, *, force: bool) -> ExtractionRun:
        now = self._now()
        run = self.runs.create(
            ExtractionRun(
                document_id=document.id,
                status=JobStatus.PROCESSING.value,
                extractor_name=EXTRACTOR_NAME,
                extractor_version=EXTRACTOR_VERSION,
                model_provider=self.provider.name,
                model_name=self.provider.model_name,
                prompt_version=self.settings.extraction_prompt_version,
                started_at=now,
                force=force,
                metadata_json={"qdrant_indexed": False},
            )
        )
        self.session.commit()
        self.session.refresh(run)
        return run

    def _mark_failed(self, run_id: UUID, failure: ExtractionError, started_at: datetime) -> None:
        self.session.rollback()
        run = self.runs.get_by_id(run_id)
        if run is None:
            return
        completed_at = self._now()
        run.status = JobStatus.FAILED.value
        run.completed_at = completed_at
        run.duration_ms = _duration_ms(started_at, completed_at)
        run.error_code = failure.code
        run.error_message = failure.safe_message
        run.metadata_json = {"details": failure.details, "qdrant_indexed": False}
        self.session.commit()

    def _get_document(self, document_id: UUID) -> Document:
        document = self.documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        return document

    def _get_ready_document(self, document_id: UUID) -> Document:
        document = self._get_document(document_id)
        if document.parse_status not in {
            ParseStatus.COMPLETED.value,
            ParseStatus.COMPLETED_WITH_WARNINGS.value,
        }:
            raise ExtractionNotReadyError(details={"parse_status": document.parse_status})
        return document

    def _now(self) -> datetime:
        return datetime.now(UTC)


def _fingerprint(document_id: UUID, chunk_id: UUID, payload: dict[str, Any]) -> str:
    stable = json.dumps(
        {
            "document_id": str(document_id),
            "chunk_id": str(chunk_id),
            "fact_type": payload.get("fact_type"),
            "equipment_tag": payload.get("equipment_tag"),
            "summary": payload.get("summary"),
            "metric_name": payload.get("metric_name"),
            "metric_value": payload.get("metric_value"),
            "work_order_number": payload.get("work_order_number"),
            "procedure_code": payload.get("procedure_code"),
            "failure_mode": payload.get("failure_mode"),
            "evidence": payload.get("evidence", {}).get("text"),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _truncate(text: str, limit: int) -> str:
    return text[:limit]


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=UTC)
    return max(0, int((completed_at - started_at).total_seconds() * 1000))


def _validation_errors(exc: Exception) -> list[dict[str, object]]:
    if isinstance(exc, ValidationError):
        return [{"message": error["msg"], "location": list(error["loc"])} for error in exc.errors()]
    return [{"message": "provider request failed safely"}]


def _event_type(value: str | None, fact_type: str) -> str:
    if fact_type == ExtractionFactType.FAILURE_EVENT.value:
        return EventType.FAILURE.value
    values = {item.value for item in EventType}
    return value if value in values else EventType.OTHER.value


def _severity(value: str | None) -> str:
    values = {item.value for item in Severity}
    return value if value in values else Severity.UNKNOWN.value


def _event_status(value: str | None) -> str:
    values = {item.value for item in EventStatus}
    return value if value in values else EventStatus.UNKNOWN.value


def _work_order_status(value: str | None) -> str:
    values = {item.value for item in WorkOrderStatus}
    return value if value in values else WorkOrderStatus.UNKNOWN.value


def _work_order_priority(value: str | None) -> str:
    values = {item.value for item in WorkOrderPriority}
    return value if value in values else WorkOrderPriority.UNKNOWN.value


def _procedure_status(value: str | None) -> str:
    values = {item.value for item in ProcedureStatus}
    return value if value in values else ProcedureStatus.DRAFT.value


def _action_status(value: str | None) -> str:
    values = {item.value for item in ActionStatus}
    return value if value in values else ActionStatus.UNKNOWN.value
