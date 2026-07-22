class IngestionError(Exception):
    status_code = 400
    code = "ingestion_error"
    safe_message = "Document ingestion failed."
    retryable = False

    def __init__(
        self, message: str | None = None, *, details: dict[str, object] | None = None
    ) -> None:
        self.message = message or self.safe_message
        self.details = details or {}
        super().__init__(self.message)


class UnsupportedFileTypeError(IngestionError):
    code = "unsupported_file_type"
    safe_message = "The file type is not supported."


class FileTooLargeError(IngestionError):
    code = "file_too_large"
    safe_message = "The file exceeds the configured upload size limit."


class EmptyFileError(IngestionError):
    code = "empty_file"
    safe_message = "The file is empty."


class InvalidFileSignatureError(IngestionError):
    code = "invalid_file_signature"
    safe_message = "The file content does not match a supported format signature."


class FileFormatMismatchError(IngestionError):
    code = "file_format_mismatch"
    safe_message = "The file extension and detected content format do not match."


class BatchTooLargeError(IngestionError):
    code = "batch_too_large"
    safe_message = "The batch contains too many files."


class DocumentNotFoundError(IngestionError):
    status_code = 404
    code = "document_not_found"
    safe_message = "Document not found."


class IngestionJobNotFoundError(IngestionError):
    status_code = 404
    code = "ingestion_job_not_found"
    safe_message = "Ingestion job not found."


class IngestionItemNotRetryableError(IngestionError):
    status_code = 409
    code = "ingestion_item_not_retryable"
    safe_message = "No failed ingestion items are retryable."


class StorageOperationError(IngestionError):
    status_code = 500
    code = "storage_operation_failed"
    safe_message = "The file could not be stored safely."
    retryable = True


class DatabaseRegistrationError(IngestionError):
    status_code = 500
    code = "database_registration_failed"
    safe_message = "The document could not be registered."
    retryable = True
