from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi import UploadFile


def upload_file(name: str, content: bytes) -> UploadFile:
    return UploadFile(BytesIO(content), filename=name)


def pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0JFIF\x00\xff\xd9"


def csv_bytes() -> bytes:
    return b"asset,value\nP-101,42\n"


def docx_bytes() -> bytes:
    return _office_zip({"[Content_Types].xml": b"<Types/>", "word/document.xml": b"<doc/>"})


def xlsx_bytes() -> bytes:
    return _office_zip({"[Content_Types].xml": b"<Types/>", "xl/workbook.xml": b"<workbook/>"})


def invalid_office_zip_bytes() -> bytes:
    return _office_zip({"[Content_Types].xml": b"<Types/>", "other/file.xml": b"<x/>"})


def _office_zip(files: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def assert_inside(path: Path, root: Path) -> None:
    assert path.resolve().is_relative_to(root.resolve())
