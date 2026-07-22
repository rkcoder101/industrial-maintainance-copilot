from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ChunkKind, ParseStatus


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_code: str
    original_filename: str
    file_type: str | None
    mime_type: str | None
    source_type: str | None
    sha256: str | None
    file_size_bytes: int | None
    page_count: int | None
    parser_name: str | None = None
    parser_version: str | None = None
    parse_status: ParseStatus
    parse_warnings_json: list[object] = Field(default_factory=list)
    parsing_started_at: datetime | None = None
    parsing_completed_at: datetime | None = None
    processing_duration_ms: int | None = None
    ocr_used: bool = False
    normalized_metadata_json: dict[str, object] = Field(default_factory=dict)
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime


class DocumentRead(DocumentListItem):
    pass


class DocumentStatusRead(BaseModel):
    id: UUID
    parse_status: ParseStatus
    uploaded_at: datetime


class DocumentProcessingRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    status: ParseStatus
    parser_name: str | None
    parser_version: str | None
    fallback_parser_name: str | None
    ocr_used: bool
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    page_count: int
    block_count: int
    chunk_count: int
    warning_count: int
    error_code: str | None
    error_message: str | None
    warnings_json: list[object]
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class DocumentProcessingStatusRead(BaseModel):
    document: DocumentRead
    latest_run: DocumentProcessingRunRead | None
    page_count: int
    block_count: int
    chunk_count: int


class ProcessingResponse(BaseModel):
    status: DocumentProcessingStatusRead


class DocumentPageListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    page_number: int
    logical_page_key: str | None
    text_content: str | None
    has_rendered_image: bool
    image_url: str | None
    width: float | None
    height: float | None
    ocr_used: bool
    ocr_confidence: float | None
    warnings_json: list[object]
    parser_metadata_json: dict[str, object]
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class DocumentBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    document_page_id: UUID | None
    block_index: int
    block_type: str
    section_path: str | None
    heading_level: int | None
    text_content: str | None
    bounding_box_json: dict[str, object] | None
    table_metadata_json: dict[str, object] | None
    parser_metadata_json: dict[str, object]
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class DocumentPageRead(DocumentPageListItem):
    blocks: list[DocumentBlockRead]


class ChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    document_page_id: UUID | None
    equipment_id: UUID | None
    chunk_index: int
    chunk_kind: ChunkKind | None
    first_page_number: int | None
    last_page_number: int | None
    section_path: str | None
    text_content: str | None
    token_count: int | None
    citation_label: str | None
    source_block_ids_json: list[object]
    equipment_hint: str | None
    bounding_box_json: dict[str, object] | None
    parser_metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class ChunkListResponse(BaseModel):
    items: list[ChunkRead]
    total: int
    page: int
    page_size: int


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    page: int
    page_size: int
