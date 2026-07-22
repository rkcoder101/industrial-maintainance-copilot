from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.documents import Document
from app.models.enums import ParseStatus
from app.services.extraction import DocumentExtractionService
from app.services.extraction_errors import ExtractionError


def extract_demo_documents(document_ids: list[UUID] | None = None, *, force: bool = False) -> int:
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
                                ParseStatus.COMPLETED.value,
                                ParseStatus.COMPLETED_WITH_WARNINGS.value,
                            ]
                        )
                    )
                    .order_by(Document.uploaded_at)
                ).all()
            )

        extracted = 0
        for document_id in target_ids:
            try:
                DocumentExtractionService(session, settings=settings).extract_document(
                    document_id,
                    force=force,
                )
                extracted += 1
            except ExtractionError as exc:
                print(f"{document_id}: {exc.code} - {exc.safe_message}")
        print(f"Extracted {extracted} document(s).")
        return extracted


if __name__ == "__main__":
    extract_demo_documents(force=True)
