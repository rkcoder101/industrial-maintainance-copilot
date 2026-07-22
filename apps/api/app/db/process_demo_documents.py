from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.documents import Document
from app.models.enums import ParseStatus
from app.services.processing import DocumentProcessingService
from app.services.processing_errors import DocumentProcessingError


def process_demo_documents(document_ids: list[UUID] | None = None, *, force: bool = False) -> int:
    settings = get_settings()
    with SessionLocal() as session:
        if document_ids:
            target_ids = document_ids
        else:
            target_ids = list(
                session.scalars(
                    select(Document.id)
                    .where(
                        Document.parse_status.in_(
                            [
                                ParseStatus.REGISTERED.value,
                                ParseStatus.FAILED.value,
                                ParseStatus.COMPLETED_WITH_WARNINGS.value,
                            ]
                        )
                    )
                    .order_by(Document.uploaded_at)
                ).all()
            )

        processed = 0
        for document_id in target_ids:
            try:
                DocumentProcessingService(session, settings=settings).process_document(
                    document_id,
                    force=force,
                )
                processed += 1
            except DocumentProcessingError as exc:
                print(f"{document_id}: {exc.code} - {exc.safe_message}")
        print(f"Processed {processed} document(s).")
        return processed


if __name__ == "__main__":
    process_demo_documents(force=True)
