import re
from dataclasses import dataclass, field
from uuid import UUID

from app.core.config import Settings
from app.models.documents import Document, DocumentBlock
from app.models.enums import BlockType, ChunkKind
from app.services.processing_errors import ChunkingError


@dataclass
class ChunkData:
    chunk_index: int
    chunk_kind: ChunkKind
    text: str
    token_count: int
    first_page_number: int | None
    last_page_number: int | None
    section_path: str | None
    citation_label: str
    source_block_ids: list[UUID] = field(default_factory=list)
    document_page_id: UUID | None = None
    equipment_hint: str | None = None
    parser_metadata: dict[str, object] = field(default_factory=dict)


class ChunkingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_chunks(self, document: Document, blocks: list[DocumentBlock]) -> list[ChunkData]:
        try:
            ordered_blocks = sorted(
                blocks,
                key=lambda block: (
                    block.page.page_number if block.page is not None else 0,
                    block.block_index,
                ),
            )
            return self._build_chunks(document, ordered_blocks)
        except Exception as exc:
            raise ChunkingError() from exc

    def _build_chunks(self, document: Document, blocks: list[DocumentBlock]) -> list[ChunkData]:
        chunks: list[ChunkData] = []
        buffer: list[DocumentBlock] = []
        buffer_tokens = 0
        active_section: str | None = None

        for block in blocks:
            text = _clean(block.text_content)
            if not text:
                continue

            if block.block_type == BlockType.HEADING.value:
                if buffer:
                    chunks.append(self._chunk_from_blocks(document, buffer, len(chunks)))
                    buffer = []
                    buffer_tokens = 0
                active_section = text
                block.section_path = block.section_path or active_section

            if block.block_type == BlockType.TABLE.value:
                if buffer:
                    chunks.append(self._chunk_from_blocks(document, buffer, len(chunks)))
                    buffer = []
                    buffer_tokens = 0
                chunks.extend(self._table_chunks(document, block, len(chunks)))
                continue

            token_count = estimate_tokens(text)
            if buffer and buffer_tokens + token_count > self.settings.chunk_max_tokens:
                chunks.append(self._chunk_from_blocks(document, buffer, len(chunks)))
                buffer = self._overlap_tail(buffer)
                buffer_tokens = sum(estimate_tokens(_clean(item.text_content)) for item in buffer)

            if active_section and not block.section_path:
                block.section_path = active_section
            buffer.append(block)
            buffer_tokens += token_count

        if buffer:
            chunks.append(self._chunk_from_blocks(document, buffer, len(chunks)))

        return chunks

    def _table_chunks(
        self,
        document: Document,
        block: DocumentBlock,
        start_index: int,
    ) -> list[ChunkData]:
        text = _clean(block.text_content)
        token_count = estimate_tokens(text)
        if token_count <= self.settings.chunk_max_tokens:
            return [self._chunk_from_blocks(document, [block], start_index)]

        lines = [line for line in text.splitlines() if line.strip()]
        chunks: list[ChunkData] = []
        current_lines: list[str] = []
        for line in lines:
            next_count = estimate_tokens("\n".join([*current_lines, line]))
            if current_lines and next_count > self.settings.chunk_max_tokens:
                chunks.append(
                    self._chunk_from_lines(
                        document, block, current_lines, start_index + len(chunks)
                    )
                )
                current_lines = []
            current_lines.append(line)
        if current_lines:
            chunks.append(
                self._chunk_from_lines(document, block, current_lines, start_index + len(chunks))
            )
        return chunks

    def _chunk_from_lines(
        self,
        document: Document,
        block: DocumentBlock,
        lines: list[str],
        chunk_index: int,
    ) -> ChunkData:
        text = "\n".join(lines)
        page_number = block.page.page_number if block.page is not None else None
        return ChunkData(
            chunk_index=chunk_index,
            chunk_kind=_kind_for_blocks([block], document),
            text=text,
            token_count=estimate_tokens(text),
            first_page_number=page_number,
            last_page_number=page_number,
            section_path=block.section_path,
            citation_label=_citation(document.document_code, page_number, page_number, chunk_index),
            source_block_ids=[block.id],
            document_page_id=block.document_page_id,
            equipment_hint=_equipment_hint(text),
            parser_metadata={"split_from_table": True},
        )

    def _chunk_from_blocks(
        self,
        document: Document,
        blocks: list[DocumentBlock],
        chunk_index: int,
    ) -> ChunkData:
        text = "\n\n".join(
            _clean(block.text_content) for block in blocks if _clean(block.text_content)
        )
        page_numbers = [
            block.page.page_number
            for block in blocks
            if block.page is not None and block.page.page_number is not None
        ]
        first_page = min(page_numbers) if page_numbers else None
        last_page = max(page_numbers) if page_numbers else None
        source_page_id = blocks[0].document_page_id if blocks else None
        return ChunkData(
            chunk_index=chunk_index,
            chunk_kind=_kind_for_blocks(blocks, document),
            text=text,
            token_count=estimate_tokens(text),
            first_page_number=first_page,
            last_page_number=last_page,
            section_path=_section_path(blocks),
            citation_label=_citation(document.document_code, first_page, last_page, chunk_index),
            source_block_ids=[block.id for block in blocks],
            document_page_id=source_page_id,
            equipment_hint=_equipment_hint(text),
        )

    def _overlap_tail(self, blocks: list[DocumentBlock]) -> list[DocumentBlock]:
        if self.settings.chunk_overlap_tokens <= 0:
            return []
        tail: list[DocumentBlock] = []
        total = 0
        for block in reversed(blocks):
            total += estimate_tokens(_clean(block.text_content))
            tail.insert(0, block)
            if total >= self.settings.chunk_overlap_tokens:
                break
        return tail


def estimate_tokens(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _kind_for_blocks(blocks: list[DocumentBlock], document: Document) -> ChunkKind:
    if any(block.block_type == BlockType.TABLE.value for block in blocks):
        return (
            ChunkKind.SPREADSHEET_ROWS if document.file_type in {"csv", "xlsx"} else ChunkKind.TABLE
        )
    if any(block.block_type == BlockType.IMAGE_TEXT.value for block in blocks):
        return ChunkKind.IMAGE_OCR
    source_type = (document.source_type or "").lower()
    text = " ".join(_clean(block.text_content).lower() for block in blocks)
    if "procedure" in source_type or re.search(r"\b(step|procedure|shutdown|startup)\b", text):
        return ChunkKind.PROCEDURE
    if "inspection" in source_type or "inspection" in text:
        return ChunkKind.INSPECTION
    if "incident" in source_type or "failure" in text:
        return ChunkKind.INCIDENT
    if "maintenance" in source_type or "maintenance" in text:
        return ChunkKind.MAINTENANCE_RECORD
    if "checklist" in text:
        return ChunkKind.CHECKLIST
    if document.file_type in {"pdf", "docx"}:
        return ChunkKind.MANUAL_SECTION
    return ChunkKind.GENERAL_TEXT


def _section_path(blocks: list[DocumentBlock]) -> str | None:
    for block in reversed(blocks):
        if block.section_path:
            return block.section_path
    return None


def _citation(
    document_code: str,
    first_page: int | None,
    last_page: int | None,
    chunk_index: int,
) -> str:
    if first_page is None:
        return f"{document_code}:c{chunk_index}"
    if last_page is None or last_page == first_page:
        return f"{document_code}:p{first_page}:c{chunk_index}"
    return f"{document_code}:p{first_page}-p{last_page}:c{chunk_index}"


def _equipment_hint(text: str) -> str | None:
    match = re.search(r"\b([A-Z]{1,4}[-_]\d{2,6}[A-Z]?)\b", text)
    if not match:
        return None
    return match.group(1)


def _clean(value: str | None) -> str:
    return (value or "").strip()
