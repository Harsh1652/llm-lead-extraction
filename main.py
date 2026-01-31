"""
Demo usage: run with python -m llm_contract.main
Uses OPENAI_API_KEY; set it or use a .env file.
"""
from __future__ import annotations

import os
import sys

# Allow running as python -m llm_contract.main from repo root
if __name__ == "__main__" and os.path.dirname(__file__) not in sys.path:
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent not in sys.path:
        sys.path.insert(0, parent)

from llm_contract.extractor import extract_lead
from llm_contract.schemas import Ok, Err


DEMO_INPUTS = [
    ("Clean input", "Hi, I'm Ankit. Email: ankit@gmail.com, phone 9876543210"),
    ("Messy input", "Call me 📞 9️⃣8️⃣7️⃣6️⃣5️⃣4️⃣3️⃣2️⃣1️⃣0️⃣ — Rohit"),
    ("Partial input", "Interested in demo, email is raj@abc.com"),
    ("Garbage input", "hello"),
]


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run demo (e.g. export OPENAI_API_KEY=sk-...)")
        return

    print("--- llm_contract demo ---\n")
    for label, text in DEMO_INPUTS:
        print(f"[{label}] input: {text[:60]!r}...")
        result = extract_lead(text)
        if isinstance(result, Ok):
            lead = result.value
            payload = lead.to_crm_payload()
            print(f"  -> Ok(name={payload['name']!r}, email={payload['email']!r}, phone={payload['phone']!r})")
        else:
            err = result.error
            print(f"  -> Err(failure_type={err.failure_type.value!r}, reason={err.reason!r})")
        print()
    print("--- done ---")


if __name__ == "__main__":
    main()
