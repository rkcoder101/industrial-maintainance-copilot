from dataclasses import dataclass
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from app.services.ingestion_errors import (
    EmptyFileError,
    FileFormatMismatchError,
    InvalidFileSignatureError,
    UnsupportedFileTypeError,
)

SUPPORTED_FORMATS: dict[str, tuple[str, str]] = {
    ".pdf": ("pdf", "application/pdf"),
    ".docx": (
        "docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    ".xlsx": (
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    ".csv": ("csv", "text/csv"),
    ".txt": ("txt", "text/plain"),
    ".png": ("png", "image/png"),
    ".jpg": ("jpeg", "image/jpeg"),
    ".jpeg": ("jpeg", "image/jpeg"),
}


@dataclass(frozen=True)
class FilenameValidationResult:
    original_filename: str
    extension: str
    expected_file_type: str
    expected_mime_type: str


@dataclass(frozen=True)
class ContentValidationResult:
    file_type: str
    mime_type: str


class FileValidationService:
    def __init__(self, allowed_extensions: frozenset[str]) -> None:
        self.allowed_extensions = allowed_extensions

    def validate_filename(self, filename: str | None) -> FilenameValidationResult:
        normalized = (filename or "").strip()
        if not normalized:
            raise UnsupportedFileTypeError("A filename is required.")
        if "\x00" in normalized:
            raise UnsupportedFileTypeError("Filenames cannot contain null bytes.")

        name = PurePosixPath(normalized.replace("\\", "/")).name
        if not name or name in {".", ".."}:
            raise UnsupportedFileTypeError("A filename is required.")

        extension = PurePosixPath(name).suffix.lower()
        if extension not in self.allowed_extensions or extension not in SUPPORTED_FORMATS:
            raise UnsupportedFileTypeError("The file extension is not supported.")

        expected_file_type, expected_mime_type = SUPPORTED_FORMATS[extension]
        return FilenameValidationResult(
            original_filename=name,
            extension=extension,
            expected_file_type=expected_file_type,
            expected_mime_type=expected_mime_type,
        )

    def validate_content(
        self,
        *,
        temp_path: str,
        header: bytes,
        size_bytes: int,
        expected: FilenameValidationResult,
    ) -> ContentValidationResult:
        if size_bytes <= 0:
            raise EmptyFileError()

        detected = self._detect_content(temp_path=temp_path, header=header, expected=expected)
        if detected.file_type != expected.expected_file_type:
            raise FileFormatMismatchError()
        return detected

    def _detect_content(
        self,
        *,
        temp_path: str,
        header: bytes,
        expected: FilenameValidationResult,
    ) -> ContentValidationResult:
        extension = expected.extension
        if extension == ".pdf":
            if header.startswith(b"%PDF-"):
                return ContentValidationResult("pdf", "application/pdf")
            raise InvalidFileSignatureError()

        if extension == ".png":
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                return ContentValidationResult("png", "image/png")
            raise InvalidFileSignatureError()

        if extension in {".jpg", ".jpeg"}:
            if header.startswith(b"\xff\xd8\xff"):
                return ContentValidationResult("jpeg", "image/jpeg")
            raise InvalidFileSignatureError()

        if extension in {".docx", ".xlsx"}:
            return self._validate_office_zip(temp_path, expected)

        if extension in {".csv", ".txt"}:
            return self._validate_text_like(header, expected)

        raise UnsupportedFileTypeError()

    def _validate_office_zip(
        self, temp_path: str, expected: FilenameValidationResult
    ) -> ContentValidationResult:
        try:
            with ZipFile(temp_path) as archive:
                names = set(archive.namelist())
        except (BadZipFile, OSError):
            raise InvalidFileSignatureError() from None

        if "[Content_Types].xml" not in names:
            raise InvalidFileSignatureError()
        if expected.extension == ".docx" and "word/document.xml" in names:
            return ContentValidationResult("docx", SUPPORTED_FORMATS[".docx"][1])
        if expected.extension == ".xlsx" and "xl/workbook.xml" in names:
            return ContentValidationResult("xlsx", SUPPORTED_FORMATS[".xlsx"][1])
        raise FileFormatMismatchError()

    def _validate_text_like(
        self, header: bytes, expected: FilenameValidationResult
    ) -> ContentValidationResult:
        if b"\x00" in header:
            raise InvalidFileSignatureError()
        control_bytes = sum(1 for byte in header if byte < 32 and byte not in {9, 10, 13})
        if header and control_bytes / len(header) > 0.05:
            raise InvalidFileSignatureError()
        try:
            header.decode("utf-8")
        except UnicodeDecodeError:
            raise InvalidFileSignatureError() from None
        return ContentValidationResult(expected.expected_file_type, expected.expected_mime_type)
