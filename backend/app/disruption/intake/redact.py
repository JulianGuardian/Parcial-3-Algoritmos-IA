"""Redaction of personal data from a passenger's free-text question.

Task 4.2 / spec "Personal data redacted before classification". Applied to
every question before it is sent to any classifier model.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Phone numbers: an optional leading "+", then digits/spaces/dashes/parens,
# at least 7 digits total. Excludes bare ISO dates (YYYY-MM-DD), which would
# otherwise look like a dash-separated phone number.
_PHONE_RE = re.compile(r"(?<!\w)(?!\d{4}-\d{2}-\d{2}(?!\d))(\+?\d[\d \-()]{6,}\d)(?!\w)")
# Chilean-style document ids such as "12.345.678-9".
_DOCUMENT_RE = re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b")


def redact_pii(text: str) -> str:
    """Return `text` with emails, phone numbers and document ids replaced."""
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _DOCUMENT_RE.sub("[REDACTED_DOCUMENT]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text
