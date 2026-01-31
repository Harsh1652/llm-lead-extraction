"""
Retry policy: max 3 attempts, exponential backoff. Retry only on invalid output or timeout.
"""
from __future__ import annotations

import logging
import time

from llm_contract.errors import (
    ExtractorError,
    FailureKind,
    ModelInvalidOutput,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY_SEC = 1.0
RETRIABLE_TYPES = (ModelInvalidOutput, LLMTimeoutError)


def is_retriable(error: ExtractorError) -> bool:
    """True only for invalid output or timeout."""
    return type(error) in RETRIABLE_TYPES


def backoff_delay(attempt: int) -> float:
    """Exponential backoff: 1s, 2s, 4s."""
    return BASE_DELAY_SEC * (2**attempt)


def with_retry(
    attempt: int,
    max_retries: int = MAX_RETRIES,
) -> bool:
    """Return True if another attempt is allowed (i.e. there is a next loop iteration)."""
    # Loop is: for attempt in range(max_retries). Next iteration exists iff attempt + 1 < max_retries.
    return attempt < max_retries - 1


def log_attempt_failure(
    attempt: int,
    failure_type: FailureKind,
    reason: str,
    will_retry: bool,
) -> None:
    """Log attempt number, failure type, reason, and retry decision."""
    msg = (
        f"attempt={attempt + 1} failure_type={failure_type.value!r} reason={reason!r} will_retry={will_retry}"
    )
    logger.warning(msg)
    # Simple print for environments without logging config
    print(f"[retry] {msg}")
