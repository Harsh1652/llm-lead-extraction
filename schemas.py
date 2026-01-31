"""
Pydantic models for lead extraction. Schema is the contract boundary.
"""
from __future__ import annotations

import re
from typing import Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field, field_validator

# Import at runtime so Err() accepts ExtractorError; errors.py does not import schemas.
from llm_contract.errors import ExtractorError

T = TypeVar("T")

# Phone: digits only, 10–15 chars (E.164-ish)
PHONE_DIGITS_MIN = 10
PHONE_DIGITS_MAX = 15


class LeadExtraction(BaseModel):
    """Extracted lead fields. All optional to support partial input."""

    name: str | None = Field(default=None, description="Full or display name")
    email: EmailStr | None = Field(default=None, description="Email address (valid format if present)")
    phone: str | None = Field(default=None, description="Phone number, digits only, 10–15 chars")

    @field_validator("email", mode="before")
    @classmethod
    def email_empty_to_none(cls, v: str | None) -> str | None:
        """Normalize empty/whitespace to None so EmailStr validation applies only when present."""
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone_format(cls, v: str | None) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        s = v.strip()
        # Normalize: keep only digits (strip spaces, dashes, parens, +prefix)
        digits = re.sub(r"\D", "", s)
        if not digits:
            raise ValueError("Phone must contain digits")
        if len(digits) < PHONE_DIGITS_MIN or len(digits) > PHONE_DIGITS_MAX:
            raise ValueError(
                f"Phone must be {PHONE_DIGITS_MIN}–{PHONE_DIGITS_MAX} digits, got {len(digits)}"
            )
        return digits

    def has_contact(self) -> bool:
        """True iff at least one of email or phone is present. Used for empty-lead policy."""
        return self.email is not None or self.phone is not None

    def to_crm_payload(self) -> dict[str, str | None]:
        """Safe for CRM insert: only schema fields, no raw LLM output."""
        return self.model_dump()


class Ok(Generic[T]):
    """Success result."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"


class Err:
    """Error result. Holds typed failure, never raw text."""

    def __init__(self, error: ExtractorError) -> None:
        self.error = error

    def __repr__(self) -> str:
        return f"Err({self.error!r})"


Result = Ok[LeadExtraction] | Err
