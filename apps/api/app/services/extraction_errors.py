class ExtractionError(Exception):
    status_code = 400
    code = "extraction_failed"
    safe_message = "Document extraction failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message or self.safe_message
        self.details = details or {}
        super().__init__(self.message)


class ExtractionDisabledError(ExtractionError):
    status_code = 409
    code = "extraction_disabled"
    safe_message = "Structured extraction is disabled."


class ExtractionNotReadyError(ExtractionError):
    status_code = 409
    code = "extraction_not_ready"
    safe_message = "Document must be successfully parsed before extraction."


class ExtractionAlreadyProcessingError(ExtractionError):
    status_code = 409
    code = "extraction_already_processing"
    safe_message = "Document extraction is already in progress."


class ExtractionRunNotFoundError(ExtractionError):
    status_code = 404
    code = "extraction_run_not_found"
    safe_message = "Extraction run was not found."


class ExtractedFactNotFoundError(ExtractionError):
    status_code = 404
    code = "extracted_fact_not_found"
    safe_message = "Extracted fact was not found."


class ExtractionRetryNotAllowedError(ExtractionError):
    status_code = 409
    code = "extraction_retry_not_allowed"
    safe_message = "Document extraction cannot be retried in its current state."


class ExtractionProviderError(ExtractionError):
    status_code = 502
    code = "extraction_provider_error"
    safe_message = "The extraction provider failed safely."
