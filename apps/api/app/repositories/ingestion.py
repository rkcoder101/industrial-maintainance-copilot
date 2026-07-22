from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import IngestionItemStatus
from app.models.jobs import IngestionItem, IngestionJob


class IngestionJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, job: IngestionJob) -> IngestionJob:
        self.session.add(job)
        return job

    def get_by_id(self, job_id: UUID) -> IngestionJob | None:
        return self.session.get(IngestionJob, job_id)

    def get_with_items(self, job_id: UUID) -> IngestionJob | None:
        query = (
            select(IngestionJob)
            .options(selectinload(IngestionJob.items))
            .where(IngestionJob.id == job_id)
        )
        return self.session.scalar(query)

    def list_items_for_job(self, job_id: UUID) -> list[IngestionItem]:
        query = select(IngestionItem).where(IngestionItem.ingestion_job_id == job_id)
        return list(
            self.session.scalars(query.order_by(IngestionItem.created_at, IngestionItem.id)).all()
        )

    def get_retryable_failed_items(self, job_id: UUID) -> list[IngestionItem]:
        query = select(IngestionItem).where(
            IngestionItem.ingestion_job_id == job_id,
            IngestionItem.status == IngestionItemStatus.FAILED.value,
            IngestionItem.error_code.in_(
                [
                    "storage_operation_failed",
                    "database_registration_failed",
                ]
            ),
        )
        return list(self.session.scalars(query.order_by(IngestionItem.created_at)).all())


class IngestionItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, item: IngestionItem) -> IngestionItem:
        self.session.add(item)
        return item

    def update_status(self, item: IngestionItem, status: str) -> IngestionItem:
        item.status = status
        return item

    def associate_document(self, item: IngestionItem, document_id: UUID) -> IngestionItem:
        item.document_id = document_id
        return item

    def mark_duplicate(self, item: IngestionItem, document_id: UUID) -> IngestionItem:
        item.duplicate_of_document_id = document_id
        item.status = IngestionItemStatus.DUPLICATE.value
        return item

    def mark_failed(
        self,
        item: IngestionItem,
        *,
        error_code: str,
        error_message: str,
    ) -> IngestionItem:
        item.status = IngestionItemStatus.FAILED.value
        item.error_code = error_code
        item.error_message = error_message
        return item

    def increment_attempt_count(self, item: IngestionItem) -> IngestionItem:
        item.attempt_count = (item.attempt_count or 0) + 1
        return item
