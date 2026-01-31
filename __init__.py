"""
llm_contract: Lead extraction from raw text via LLM with strict contract.
"""
from llm_contract.extractor import extract_lead, LLMCall
from llm_contract.schemas import LeadExtraction, Result, Ok, Err
from llm_contract.errors import (
    EmptyLead,
    ExtractorError,
    FailureKind,
    ModelInvalidOutput,
    LLMTimeoutError,
    ProviderError,
)

__all__ = [
    "extract_lead",
    "LLMCall",
    "LeadExtraction",
    "Result",
    "Ok",
    "Err",
    "EmptyLead",
    "ExtractorError",
    "FailureKind",
    "ModelInvalidOutput",
    "LLMTimeoutError",
    "ProviderError",
]
