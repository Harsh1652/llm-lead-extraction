Backend module: accepts raw text (webhook/form), calls an LLM to extract lead data, enforces a strict Pydantic contract, and returns deterministic `Result[LeadExtraction]`. Never leaks raw LLM output.

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
```

Optional: `OPENAI_EXTRACTION_MODEL` (default: `gpt-4o-mini`).

## Usage

```python
from llm_contract import extract_lead, Ok, Err, FailureKind

result = extract_lead("Hi, I'm Ankit. Email: ankit@gmail.com, phone 9876543210")

if isinstance(result, Ok):
    payload = result.value.to_crm_payload()  # Safe for CRM insert
else:
    err = result.error
    if err.failure_type == FailureKind.EMPTY_LEAD:
        # No email or phone extracted
        ...
    elif err.failure_type == FailureKind.PROVIDER_ERROR:
        ...
    print(err.failure_type.value, err.reason)
```

**Inject LLM call (e.g. for tests):**

```python
# No network; you control the response.
result = extract_lead(
    text,
    llm_call=lambda t: '{"name":"Test","email":"a@b.com","phone":"1234567890"}',
)
```

## Demo

```bash
python -m llm_contract.main
```

Runs four example inputs: clean, messy, partial, and garbage.

## API

- **`extract_lead(text: str, *, llm_call: LLMCall | None = None) -> Result`**
- **Success:** `Ok(LeadExtraction)` — at least one of `email` or `phone` (empty leads are rejected).
- **Failure:** `Err(ExtractorError)` — `error.failure_type` is a `FailureKind` enum; `error.reason` is a string.
- Raw LLM output is never returned.

## Contract

- **Schema:** `LeadExtraction` has `name`, `email`, `phone` (all optional). Email validated with Pydantic `EmailStr`; phone normalized to digits only, 10–15 chars.
- **Empty-lead policy:** If the LLM returns valid JSON with no email and no phone, we return `Err(EmptyLead(...))`. Downstream never receives a lead with no contact info.
- **Result:** Either `Ok(lead)` or `Err(ExtractorError)`; all failures are typed via `FailureKind`.

## Failure types (`FailureKind`)

| Kind | Meaning |
|------|--------|
| `MODEL_INVALID_OUTPUT` | Invalid JSON or Pydantic validation failed |
| `TIMEOUT` | LLM call timed out |
| `PROVIDER_ERROR` | API key, auth, or provider error (not retried) |
| `EMPTY_LEAD` | Valid extraction but no email and no phone |

## Retries

- **Max attempts:** 3  
- **Retried:** `MODEL_INVALID_OUTPUT`, `TIMEOUT`  
- **Not retried:** `PROVIDER_ERROR`, `EMPTY_LEAD`  
- **Backoff:** 1s, 2s, 4s (exponential)  
- Each failure logs: attempt number, failure type, reason, `will_retry`.

## Project layout

```
llm_contract/
├── extractor.py   # extract_lead(), LLM call, parse, validate, retry loop
├── schemas.py     # LeadExtraction, Result, Ok, Err, validators
├── errors.py      # FailureKind, ExtractorError and subclasses
├── retry.py       # Retry policy and backoff
├── main.py        # Demo
└── __init__.py    # Public API
```
