"""Deterministic validator for the answer agent's draft (task 6.2, design D13).

The draft is rejected - and the template answer used instead - if it:
- mentions a flight/option other than the recommended one;
- lacks the `policy_ref`;
- contains personal data (email, phone, document id);
- claims the booking was changed or compensation was approved;
- contradicts `requires_human`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.disruption.contracts import Decision
from app.disruption.intake.redact import _DOCUMENT_RE, _EMAIL_RE, _PHONE_RE

_FORBIDDEN_CLAIMS = (
    "booking changed",
    "booking has been changed",
    "compensation approved",
    "compensation has been approved",
    "your compensation was approved",
)


@dataclass
class ValidationResult:
    accepted: bool
    reason: str | None = None


def _mentions_other_flight(draft: str, recommended_flight: str | None) -> bool:
    flight_numbers = set(re.findall(r"\b[A-Z]{2}\d{3,4}\b", draft))
    if recommended_flight:
        flight_numbers.discard(recommended_flight)
    return bool(flight_numbers)


def validate_answer_draft(draft: str, decision: Decision) -> ValidationResult:
    recommended = decision.recommended_option
    recommended_flight = recommended.flight_number if recommended is not None else None

    if _mentions_other_flight(draft, recommended_flight):
        return ValidationResult(False, "mentions_other_option")

    if decision.policy_ref and decision.policy_ref not in draft:
        return ValidationResult(False, "missing_policy_ref")

    if _EMAIL_RE.search(draft) or _PHONE_RE.search(draft) or _DOCUMENT_RE.search(draft):
        return ValidationResult(False, "contains_personal_data")

    lowered = draft.lower()
    if any(claim in lowered for claim in _FORBIDDEN_CLAIMS):
        return ValidationResult(False, "overclaims_outcome")

    if decision.requires_human and "agent" not in lowered and "human" not in lowered:
        return ValidationResult(False, "contradicts_requires_human")

    return ValidationResult(True)
