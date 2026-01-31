"""
Typed failure types for the extractor. All failures are explainable; no raw LLM output.
"""
from __future__ import annotations

from enum import Enum


class FailureKind(str, Enum):
    """Strongly-typed failure kind for matching and logging. Not free-form strings."""

    EXTRACTOR_ERROR = "EXTRACTOR_ERROR"
    MODEL_INVALID_OUTPUT = "MODEL_INVALID_OUTPUT"
    TIMEOUT = "TIMEOUT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    EMPTY_LEAD = "EMPTY_LEAD"


class ExtractorError(Exception):
    """Base type for all extractor failures."""

    failure_type: FailureKind = FailureKind.EXTRACTOR_ERROR
    reason: str = ""

    def __init__(self, reason: str, failure_type: FailureKind | None = None) -> None:
        self.reason = reason
        if failure_type is not None:
            self.failure_type = failure_type
        super().__init__(reason)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(failure_type={self.failure_type!r}, reason={self.reason!r})"


class ModelInvalidOutput(ExtractorError):
    """LLM returned invalid JSON or output failed Pydantic validation."""

    failure_type = FailureKind.MODEL_INVALID_OUTPUT


class LLMTimeoutError(ExtractorError):
    """LLM call timed out."""

    failure_type = FailureKind.TIMEOUT


class ProviderError(ExtractorError):
    """API / provider error (auth, rate limit, etc.). Not retried."""

    failure_type = FailureKind.PROVIDER_ERROR


class EmptyLead(ExtractorError):
    """Valid extraction but no contact info (no email and no phone). Policy: do not return Ok."""

    failure_type = FailureKind.EMPTY_LEAD
