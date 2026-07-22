import pytest

from app.services.file_validation import FileValidationService
from app.services.ingestion_errors import (
    EmptyFileError,
    FileFormatMismatchError,
    InvalidFileSignatureError,
    UnsupportedFileTypeError,
)
from tests.ingestion_helpers import (
    csv_bytes,
    docx_bytes,
    invalid_office_zip_bytes,
    jpeg_bytes,
    pdf_bytes,
    png_bytes,
    xlsx_bytes,
)


@pytest.fixture
def validator() -> FileValidationService:
    return FileValidationService(
        frozenset({".pdf", ".docx", ".xlsx", ".csv", ".txt", ".png", ".jpg", ".jpeg"})
    )


def test_filename_validation_normalizes_path_like_names(validator: FileValidationService) -> None:
    result = validator.validate_filename("../evil manual.pdf")

    assert result.original_filename == "evil manual.pdf"
    assert result.extension == ".pdf"


def test_filename_validation_allows_spaces_and_unicode(validator: FileValidationService) -> None:
    filename = "Pump P-101 r\u00e9sum\u00e9.pdf"
    result = validator.validate_filename(filename)

    assert result.original_filename == filename


def test_filename_validation_rejects_null_bytes(validator: FileValidationService) -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validator.validate_filename("evil\x00.pdf")


def test_content_validation_supported_formats(validator: FileValidationService, tmp_path) -> None:
    cases = [
        ("manual.pdf", pdf_bytes(), "pdf"),
        ("image.png", png_bytes(), "png"),
        ("photo.jpg", jpeg_bytes(), "jpeg"),
        ("report.docx", docx_bytes(), "docx"),
        ("trend.xlsx", xlsx_bytes(), "xlsx"),
        ("inspection.csv", csv_bytes(), "csv"),
        ("notes.txt", b"plain maintenance note\n", "txt"),
    ]
    for filename, content, file_type in cases:
        temp_path = tmp_path / filename
        temp_path.write_bytes(content)
        expected = validator.validate_filename(filename)

        detected = validator.validate_content(
            temp_path=str(temp_path),
            header=content[:8192],
            size_bytes=len(content),
            expected=expected,
        )

        assert detected.file_type == file_type


def test_content_validation_rejects_invalid_pdf_signature(
    validator: FileValidationService, tmp_path
) -> None:
    temp_path = tmp_path / "manual.pdf"
    temp_path.write_bytes(b"MZ executable")
    expected = validator.validate_filename("manual.pdf")

    with pytest.raises(InvalidFileSignatureError):
        validator.validate_content(
            temp_path=str(temp_path), header=b"MZ executable", size_bytes=13, expected=expected
        )


def test_content_validation_rejects_invalid_docx_zip(
    validator: FileValidationService, tmp_path
) -> None:
    content = invalid_office_zip_bytes()
    temp_path = tmp_path / "manual.docx"
    temp_path.write_bytes(content)
    expected = validator.validate_filename("manual.docx")

    with pytest.raises(FileFormatMismatchError):
        validator.validate_content(
            temp_path=str(temp_path),
            header=content[:8192],
            size_bytes=len(content),
            expected=expected,
        )


def test_content_validation_rejects_binary_text(validator: FileValidationService, tmp_path) -> None:
    content = b"hello\x00world"
    temp_path = tmp_path / "notes.txt"
    temp_path.write_bytes(content)
    expected = validator.validate_filename("notes.txt")

    with pytest.raises(InvalidFileSignatureError):
        validator.validate_content(
            temp_path=str(temp_path),
            header=content,
            size_bytes=len(content),
            expected=expected,
        )


def test_content_validation_rejects_empty_files(validator: FileValidationService, tmp_path) -> None:
    temp_path = tmp_path / "empty.txt"
    temp_path.write_bytes(b"")
    expected = validator.validate_filename("empty.txt")

    with pytest.raises(EmptyFileError):
        validator.validate_content(
            temp_path=str(temp_path), header=b"", size_bytes=0, expected=expected
        )


def test_content_validation_rejects_unsupported_extension(validator: FileValidationService) -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validator.validate_filename("archive.zip")
