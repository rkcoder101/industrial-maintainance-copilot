class DocumentProcessingError(Exception):
    status_code = 400
    code = "document_processing_failed"
    safe_message = "Document processing failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message or self.safe_message
        self.details = details or {}
        super().__init__(self.message)


class DocumentProcessingNotFoundError(DocumentProcessingError):
    status_code = 404
    code = "document_processing_not_found"
    safe_message = "Document processing run not found."


class DocumentAlreadyProcessingError(DocumentProcessingError):
    status_code = 409
    code = "document_already_processing"
    safe_message = "Document processing is already in progress."


class StoredDocumentMissingError(DocumentProcessingError):
    status_code = 404
    code = "stored_document_missing"
    safe_message = "Stored document file is missing."


class UnsupportedParserError(DocumentProcessingError):
    code = "unsupported_parser"
    safe_message = "No parser is available for this document type."


class DocumentParseError(DocumentProcessingError):
    status_code = 500
    code = "document_parse_error"
    safe_message = "The document could not be parsed safely."


class PageRenderError(DocumentProcessingError):
    status_code = 500
    code = "page_render_error"
    safe_message = "The page could not be rendered safely."


class OCRProcessingError(DocumentProcessingError):
    status_code = 500
    code = "ocr_processing_error"
    safe_message = "OCR could not be completed safely."


class NormalizationError(DocumentProcessingError):
    status_code = 500
    code = "normalization_error"
    safe_message = "The parsed document could not be normalized safely."


class ChunkingError(DocumentProcessingError):
    status_code = 500
    code = "chunking_error"
    safe_message = "Document chunks could not be generated safely."


class ProcessingRetryNotAllowedError(DocumentProcessingError):
    status_code = 409
    code = "processing_retry_not_allowed"
    safe_message = "Document processing cannot be retried in its current state."
