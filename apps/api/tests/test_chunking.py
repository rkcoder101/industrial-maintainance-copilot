from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.documents import Document, DocumentBlock, DocumentPage
from app.models.enums import BlockType, ParseStatus
from app.services.chunking import ChunkingService


def _document(session: Session, *, file_type: str = "pdf", source_type: str = "manual") -> Document:
    document = Document(
        id=uuid4(),
        document_code="DOC-TEST000001",
        original_filename="manual.pdf",
        file_type=file_type,
        source_type=source_type,
        parse_status=ParseStatus.PROCESSING.value,
    )
    page = DocumentPage(document=document, page_number=1, logical_page_key="page-1")
    session.add_all([document, page])
    session.flush()
    return document


def _block(
    session: Session,
    document: Document,
    *,
    index: int,
    text: str,
    block_type: BlockType = BlockType.PARAGRAPH,
    section_path: str | None = "P-101 PUMP",
) -> DocumentBlock:
    page = document.pages[0]
    block = DocumentBlock(
        document_id=document.id,
        document_page_id=page.id,
        page=page,
        block_index=index,
        block_type=block_type.value,
        section_path=section_path,
        text_content=text,
    )
    session.add(block)
    session.flush()
    return block


def test_chunking_preserves_source_blocks_and_page_spans(db_session: Session, tmp_path) -> None:
    document = _document(db_session)
    heading = _block(
        db_session,
        document,
        index=0,
        text="P-101 PUMP",
        block_type=BlockType.HEADING,
    )
    paragraph = _block(
        db_session,
        document,
        index=1,
        text="Inspect P-101 bearing temperature before startup.",
    )
    settings = Settings(
        app_env="test",
        upload_dir=str(tmp_path / "uploads"),
        chunk_target_tokens=20,
        chunk_max_tokens=30,
        chunk_overlap_tokens=0,
    )

    chunks = ChunkingService(settings).build_chunks(document, [heading, paragraph])

    assert len(chunks) == 1
    assert chunks[0].first_page_number == 1
    assert chunks[0].last_page_number == 1
    assert chunks[0].source_block_ids == [heading.id, paragraph.id]
    assert chunks[0].citation_label == "DOC-TEST000001:p1:c0"
    assert chunks[0].equipment_hint == "P-101"


def test_chunking_keeps_tables_as_spreadsheet_chunks(db_session: Session, tmp_path) -> None:
    document = _document(db_session, file_type="csv", source_type="inspection")
    table = _block(
        db_session,
        document,
        index=0,
        text="Asset | Reading\nP-101 | 42",
        block_type=BlockType.TABLE,
    )
    settings = Settings(app_env="test", upload_dir=str(tmp_path / "uploads"))

    chunks = ChunkingService(settings).build_chunks(document, [table])

    assert len(chunks) == 1
    assert chunks[0].chunk_kind.value == "spreadsheet_rows"
    assert chunks[0].source_block_ids == [table.id]


def test_chunking_applies_overlap_when_splitting(db_session: Session, tmp_path) -> None:
    document = _document(db_session)
    blocks = [
        _block(db_session, document, index=index, text=f"Paragraph {index} P-101 details")
        for index in range(4)
    ]
    settings = Settings(
        app_env="test",
        upload_dir=str(tmp_path / "uploads"),
        chunk_target_tokens=4,
        chunk_max_tokens=7,
        chunk_overlap_tokens=4,
    )

    chunks = ChunkingService(settings).build_chunks(document, blocks)

    assert len(chunks) >= 2
    assert blocks[1].id in chunks[1].source_block_ids
