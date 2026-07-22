from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.services.parsers import (
    CSVParser,
    DocxParser,
    ImageOCRParser,
    OpenPyXLParser,
    ParserRegistry,
    PlainTextParser,
    PyMuPDFParser,
)
from app.services.parsing_contracts import ParseContext
from app.services.processing_errors import UnsupportedParserError
from app.services.storage import LocalStorageBackend, RenderedPageStorageService
from tests.ingestion_helpers import (
    csv_bytes,
    valid_docx_bytes,
    valid_pdf_bytes,
    valid_png_bytes,
    valid_xlsx_bytes,
)


def _context(tmp_path: Path, file_path: Path, file_type: str) -> ParseContext:
    settings = Settings(
        app_env="test",
        upload_dir=str(tmp_path / "uploads"),
        parsed_dir=str(tmp_path / "parsed"),
        rendered_pages_dir=str(tmp_path / "rendered-pages"),
    )
    document_id = uuid4()
    return ParseContext(
        document_id=document_id,
        document_code=f"DOC-{document_id.hex[:12].upper()}",
        file_path=file_path,
        file_type=file_type,
        mime_type=None,
        source_type="manual",
        settings=settings,
        rendered_storage=RenderedPageStorageService(
            LocalStorageBackend(settings.rendered_pages_root_path)
        ),
    )


def _write(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def test_registry_selects_expected_parsers() -> None:
    registry = ParserRegistry()

    assert isinstance(registry.get_parser("pdf", None), PyMuPDFParser)
    assert isinstance(registry.get_parser("docx", None), DocxParser)
    assert isinstance(registry.get_parser("xlsx", None), OpenPyXLParser)
    assert isinstance(registry.get_parser("csv", None), CSVParser)
    assert isinstance(registry.get_parser("txt", None), PlainTextParser)
    assert isinstance(registry.get_parser("png", None), ImageOCRParser)
    with pytest.raises(UnsupportedParserError):
        registry.get_parser("exe", None)


def test_pdf_parser_extracts_text_blocks_and_rendered_image(tmp_path: Path) -> None:
    path = _write(tmp_path, "manual.pdf", valid_pdf_bytes(["P-101 PUMP\nInspect seal pressure."]))
    context = _context(tmp_path, path, "pdf")

    parsed = PyMuPDFParser().parse(context)

    assert parsed.page_count == 1
    assert parsed.fallback_parser_name == "docling"
    assert parsed.pages[0].rendered_image_key is not None
    assert parsed.pages[0].text
    assert parsed.pages[0].blocks
    assert context.rendered_storage.backend.resolve_key(
        parsed.pages[0].rendered_image_key
    ).is_file()


@pytest.mark.parametrize(
    ("parser_factory", "name", "content", "file_type", "expected"),
    [
        (DocxParser, "manual.docx", valid_docx_bytes, "docx", "Lock out P-101"),
        (OpenPyXLParser, "inspection.xlsx", valid_xlsx_bytes, "xlsx", "P-101"),
        (CSVParser, "inspection.csv", csv_bytes, "csv", "asset | value"),
    ],
)
def test_structured_parsers_extract_blocks(
    tmp_path: Path,
    parser_factory: type[DocxParser] | type[OpenPyXLParser] | type[CSVParser],
    name: str,
    content: Callable[[], bytes],
    file_type: str,
    expected: str,
) -> None:
    path = _write(tmp_path, name, content())
    parsed = parser_factory().parse(_context(tmp_path, path, file_type))

    assert parsed.page_count >= 1
    assert expected in parsed.pages[0].text
    assert parsed.pages[0].blocks


def test_plain_text_parser_detects_heading(tmp_path: Path) -> None:
    path = _write(tmp_path, "note.txt", b"P-101 PUMP\n\nInspect bearing temperature.")

    parsed = PlainTextParser().parse(_context(tmp_path, path, "txt"))

    assert parsed.pages[0].blocks[0].block_type.value == "heading"
    assert parsed.pages[0].blocks[1].section_path == "P-101 PUMP"


def test_image_ocr_parser_uses_mocked_tesseract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write(tmp_path, "photo.png", valid_png_bytes())
    monkeypatch.setattr("app.services.parsers.shutil.which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setattr(
        "app.services.parsers.pytesseract.image_to_data",
        lambda *_args, **_kwargs: {"text": ["P-101", "OK"], "conf": ["90", "80"]},
    )

    parsed = ImageOCRParser().parse(_context(tmp_path, path, "png"))

    assert parsed.ocr_used is True
    assert parsed.pages[0].ocr_confidence == 0.85
    assert "P-101 OK" in parsed.pages[0].text
    assert parsed.pages[0].rendered_image_key is not None
