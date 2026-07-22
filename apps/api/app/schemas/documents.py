from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ParseStatus


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
    parse_status: ParseStatus
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime


class DocumentRead(DocumentListItem):
    pass


class DocumentStatusRead(BaseModel):
    id: UUID
    parse_status: ParseStatus
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    page: int
    page_size: int
