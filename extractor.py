"""
Main extraction logic. Contract boundary: extract_lead() never returns raw LLM output.
LLM call is isolated: inject llm_call to avoid side effects (network, env) in tests.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Callable

from pydantic import ValidationError

from llm_contract.errors import (
    EmptyLead,
    ExtractorError,
    ModelInvalidOutput,
    LLMTimeoutError,
    ProviderError,
)
from llm_contract.retry import (
    is_retriable,
    backoff_delay,
    with_retry,
    log_attempt_failure,
    MAX_RETRIES,
)
from llm_contract.schemas import LeadExtraction, Result, Ok, Err

logger = logging.getLogger(__name__)

# Prompt discipline: only instruct format; schema enforces structure.
EXTRACTION_SYSTEM = """You extract lead fields from raw text. Return ONLY valid JSON.
Use exactly these keys: name, email, phone. Use null for any missing value.
Do not add other keys or text."""

EXTRACTION_USER_TEMPLATE = """Extract lead data from this text. Return ONLY valid JSON with keys: name, email, phone. Use null for missing values.

Text:
{text}
"""

DEFAULT_TIMEOUT_SEC = 30.0

# Isolated LLM boundary: (text) -> raw string; may raise ExtractorError.
LLMCall = Callable[[str], str]


def _call_llm(text: str, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> str:
    """Call LLM and return raw response content. Raises ExtractorError on failure."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ProviderError("openai package not installed; pip install openai") from None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ProviderError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    user_content = EXTRACTION_USER_TEMPLATE.format(text=text)

    try:
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_EXTRACTION_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            timeout=timeout_sec,
        )
    except Exception as e:
        err_name = type(e).__name__
        if "timeout" in err_name.lower() or "Timeout" in str(e):
            raise LLMTimeoutError(str(e))
        if "Authentication" in str(e) or "api_key" in str(e).lower():
            raise ProviderError(str(e))
        raise ProviderError(str(e))

    choice = response.choices[0] if response.choices else None
    if not choice or not getattr(choice, "message", None):
        raise ModelInvalidOutput("Empty or missing message in response")

    content = (choice.message.content or "").strip()
    if not content:
        raise ModelInvalidOutput("Empty message content")

    return content


def _parse_and_validate(raw: str) -> LeadExtraction:
    """Parse JSON and validate with Pydantic. Raises ModelInvalidOutput on any failure."""
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ModelInvalidOutput(f"Invalid JSON: {e}") from e

    if not isinstance(obj, dict):
        raise ModelInvalidOutput("Response is not a JSON object")

    try:
        return LeadExtraction(
            name=obj.get("name"),
            email=obj.get("email"),
            phone=obj.get("phone"),
        )
    except ValidationError as e:
        raise ModelInvalidOutput(f"Schema validation failed: {e}") from e


def extract_lead(text: str, *, llm_call: LLMCall | None = None) -> Result:
    """
    Extract lead data from raw text. Contract boundary: never returns raw LLM output.
    Returns Ok(LeadExtraction) or Err(ExtractorError). All failures are typed.

    Empty-lead policy: we never return Ok(lead) when the lead has no email and no phone.
    Such cases return Err(EmptyLead(...)) so downstream never receives an empty lead.

    LLM call is isolated: pass llm_call to inject the LLM (e.g. for tests); side effects
    (network, env) live only in that callable. If llm_call is None, uses default OpenAI call.
    """
    last_error: ExtractorError | None = None
    call: LLMCall = llm_call if llm_call is not None else _call_llm

    for attempt in range(MAX_RETRIES):
        try:
            raw = call(text)
            lead = _parse_and_validate(raw)
            # Empty-lead policy: never return Ok when there is no contact info.
            if not lead.has_contact():
                raise EmptyLead("No email or phone extracted; lead has no contact info")
            return Ok(lead)
        except ExtractorError as e:
            last_error = e
            will_retry = with_retry(attempt, MAX_RETRIES) and is_retriable(e)
            log_attempt_failure(
                attempt=attempt,
                failure_type=e.failure_type,
                reason=e.reason,
                will_retry=will_retry,
            )
            if not will_retry:
                return Err(e)
            delay = backoff_delay(attempt)
            logger.info("retry in %.1fs", delay)
            time.sleep(delay)

    # Exhausted retries; return last error (retriable type)
    return Err(last_error) if last_error else Err(
        ModelInvalidOutput("Max retries exceeded without success")
    )
