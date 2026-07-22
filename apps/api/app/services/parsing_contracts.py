from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from app.core.config import Settings
from app.models.enums import BlockType
from app.services.storage import RenderedPageStorageService

PARSER_VERSION = "phase-04-v1"


@dataclass(frozen=True)
class ParserWarning:
    code: str
    message: str
    scope: str
    page_number: int | None = None

    def as_dict(self) -> dict[str, str | int | None]:
        return {
            "code": self.code,
            "message": self.message,
            "scope": self.scope,
            "page_number": self.page_number,
        }


@dataclass(frozen=True)
class ParseContext:
    document_id: UUID
    document_code: str
    file_path: Path
    file_type: str | None
    mime_type: str | None
    source_type: str | None
    settings: Settings
    rendered_storage: RenderedPageStorageService


@dataclass
class ParsedBlockData:
    block_index: int
    block_type: BlockType
    text: str
    page_number: int = 1
    section_path: str | None = None
    heading_level: int | None = None
    bounding_box: dict[str, float] | None = None
    table_metadata: dict[str, object] | None = None
    parser_metadata: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class ParsedPageData:
    page_number: int
    logical_page_key: str
    text: str
    blocks: list[ParsedBlockData] = field(default_factory=list)
    rendered_image_key: str | None = None
    width: float | None = None
    height: float | None = None
    ocr_used: bool = False
    ocr_confidence: float | None = None
    warnings: list[ParserWarning] = field(default_factory=list)
    parser_metadata: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class ParsedDocumentData:
    parser_name: str
    parser_version: str
    pages: list[ParsedPageData]
    warnings: list[ParserWarning] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    fallback_parser_name: str | None = None
    ocr_used: bool = False

    @property
    def page_count(self) -> int:
        return len(self.pages)
