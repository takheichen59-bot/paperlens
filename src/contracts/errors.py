"""Safe exceptions. Only controlled summaries enter to_dict() or str(error)."""
from .enums import ErrorKind, Stage

_MESSAGES = {
    ErrorKind.NOT_FOUND: "Paper not found.",
    ErrorKind.AMBIGUOUS_INPUT: "Input matches multiple papers.",
    ErrorKind.RATE_LIMITED: "Source rate limit reached.",
    ErrorKind.NETWORK_TIMEOUT: "Source request timed out.",
    ErrorKind.INVALID_DOWNLOAD: "Downloaded file is invalid.",
    ErrorKind.PDF_CORRUPTED: "PDF cannot be read.",
    ErrorKind.NEEDS_OCR: "PDF requires OCR.",
    ErrorKind.PARSE_FAILED: "Paper parsing failed.",
    ErrorKind.EXTRACT_FAILED: "Information extraction failed.",
    ErrorKind.VALIDATION_FAILED: "Record validation failed.",
    ErrorKind.UNKNOWN: "An unclassified operation failed.",
}


class ContractError(Exception):
    """Original cause is retained in memory, but never serialized.

    safe_message must be a controlled catalog value. Arbitrary strings are
    rejected rather than relying on imperfect secret-pattern redaction.
    Do not use traceback logging when only sanitized logs are permitted: Python
    exception chaining intentionally retains the original cause for debugging.
    """
    def __init__(self, stage: Stage, error_kind: ErrorKind, retryable: bool,
                 safe_message: str | None = None,
                 cause: BaseException | None = None) -> None:
        if not isinstance(stage, Stage) or not isinstance(error_kind, ErrorKind):
            raise TypeError("stage and error_kind require enum instances")
        if type(retryable) is not bool:
            raise TypeError("retryable must be bool")
        if safe_message is not None and safe_message != _MESSAGES[error_kind]:
            raise ValueError("safe_message must match the controlled error catalog")
        if cause is not None and not isinstance(cause, BaseException):
            raise TypeError("cause must be an exception or None")
        self.stage = stage
        self.error_kind = error_kind
        self.retryable = retryable
        self.safe_message = _MESSAGES[error_kind]
        self.cause = cause
        self.__cause__ = cause
        super().__init__(self.safe_message)

    def to_dict(self) -> dict[str, str | bool]:
        # Never inspect cause, request, headers, body, or arbitrary message text.
        return {
            "stage": self.stage.value,
            "error_kind": self.error_kind.value,
            "retryable": self.retryable,
            "safe_message": _MESSAGES[self.error_kind],
        }

    @classmethod
    def from_exception(cls, exception: BaseException, *, stage: Stage,
                       error_kind: ErrorKind | None = None,
                       retryable: bool | None = None) -> "ContractError":
        if not isinstance(exception, BaseException):
            raise TypeError("exception must be an exception")
        if error_kind is None:
            if isinstance(exception, ContractError):
                error_kind = exception.error_kind
            elif isinstance(exception, TimeoutError):
                error_kind = ErrorKind.NETWORK_TIMEOUT
            else:
                from pydantic import ValidationError
                error_kind = (ErrorKind.VALIDATION_FAILED
                              if isinstance(exception, ValidationError)
                              else ErrorKind.UNKNOWN)
        if retryable is None:
            retryable = (exception.retryable if isinstance(exception, ContractError)
                         else error_kind in {ErrorKind.RATE_LIMITED, ErrorKind.NETWORK_TIMEOUT})
        return cls(stage, error_kind, retryable, cause=exception)
