from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.documents import Chunk, DocumentBlock, DocumentPage, DocumentProcessingRun


class DocumentPageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, page: DocumentPage) -> DocumentPage:
        self.session.add(page)
        return page

    def list_for_document(self, document_id: UUID) -> list[DocumentPage]:
        return list(
            self.session.scalars(
                select(DocumentPage)
                .where(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_number)
            ).all()
        )

    def get_by_number(self, document_id: UUID, page_number: int) -> DocumentPage | None:
        return self.session.scalar(
            select(DocumentPage).where(
                DocumentPage.document_id == document_id,
                DocumentPage.page_number == page_number,
            )
        )

    def delete_for_document(self, document_id: UUID) -> None:
        self.session.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))


class DocumentBlockRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, block: DocumentBlock) -> DocumentBlock:
        self.session.add(block)
        return block

    def list_for_document(self, document_id: UUID) -> list[DocumentBlock]:
        return list(
            self.session.scalars(
                select(DocumentBlock)
                .options(selectinload(DocumentBlock.page))
                .where(DocumentBlock.document_id == document_id)
                .order_by(DocumentBlock.block_index)
            ).all()
        )

    def list_for_page(self, page_id: UUID) -> list[DocumentBlock]:
        return list(
            self.session.scalars(
                select(DocumentBlock)
                .where(DocumentBlock.document_page_id == page_id)
                .order_by(DocumentBlock.block_index)
            ).all()
        )

    def delete_for_document(self, document_id: UUID) -> None:
        self.session.execute(delete(DocumentBlock).where(DocumentBlock.document_id == document_id))


class ChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, chunk: Chunk) -> Chunk:
        self.session.add(chunk)
        return chunk

    def get_by_id(self, document_id: UUID, chunk_id: UUID) -> Chunk | None:
        return self.session.scalar(
            select(Chunk).where(Chunk.document_id == document_id, Chunk.id == chunk_id)
        )

    def list_for_document(
        self,
        document_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        chunk_kind: str | None = None,
    ) -> tuple[list[Chunk], int]:
        filters = [Chunk.document_id == document_id]
        if chunk_kind:
            filters.append(Chunk.chunk_kind == chunk_kind)
        total = self.session.scalar(select(func.count()).select_from(Chunk).where(*filters)) or 0
        items = list(
            self.session.scalars(
                select(Chunk)
                .where(*filters)
                .order_by(Chunk.chunk_index)
                .limit(page_size)
                .offset((page - 1) * page_size)
            ).all()
        )
        return items, total

    def delete_for_document(self, document_id: UUID) -> None:
        self.session.execute(delete(Chunk).where(Chunk.document_id == document_id))


class ProcessingRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, run: DocumentProcessingRun) -> DocumentProcessingRun:
        self.session.add(run)
        return run

    def list_for_document(self, document_id: UUID) -> list[DocumentProcessingRun]:
        return list(
            self.session.scalars(
                select(DocumentProcessingRun)
                .where(DocumentProcessingRun.document_id == document_id)
                .order_by(
                    DocumentProcessingRun.started_at.desc(), DocumentProcessingRun.created_at.desc()
                )
            ).all()
        )

    def latest_for_document(self, document_id: UUID) -> DocumentProcessingRun | None:
        return self.session.scalar(
            select(DocumentProcessingRun)
            .where(DocumentProcessingRun.document_id == document_id)
            .order_by(
                DocumentProcessingRun.started_at.desc(), DocumentProcessingRun.created_at.desc()
            )
            .limit(1)
        )
