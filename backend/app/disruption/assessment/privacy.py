"""PII stripping: the only place raw passenger data is read.

Downstream layers receive `PassengerView` objects. `document_id` and surnames
are dropped; email and phone are masked; first names are kept.
"""

import re
from typing import Any

from app.disruption.contracts import PassengerView

_MINOR_TYPES = {"CHILD", "INFANT"}
_ADULT_AGE = 18


def mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    local, domain = email.split("@", 1)
    return f"{local[:1]}***@{domain}"


def mask_phone(phone: str | None) -> str | None:
    """Replace every digit except the last four with `*`."""
    if not phone:
        return None
    total = sum(ch.isdigit() for ch in phone)
    seen = 0
    out = []
    for ch in phone:
        if ch.isdigit():
            seen += 1
            out.append(ch if seen > total - 4 else "*")
        else:
            out.append(ch)
    return "".join(out)


def first_name(full_name: str | None) -> str:
    parts = re.split(r"\s+", (full_name or "").strip())
    return parts[0] if parts and parts[0] else "Passenger"


def to_passenger_view(raw: dict[str, Any]) -> PassengerView:
    return PassengerView(
        passenger_id=raw["passenger_id"],
        first_name=first_name(raw.get("name")),
        type=raw.get("type", "ADULT"),
        age=raw.get("age"),
        masked_email=mask_email(raw.get("email")),
        masked_phone=mask_phone(raw.get("phone")),
    )


def is_minor(raw: dict[str, Any]) -> bool:
    if raw.get("type") in _MINOR_TYPES:
        return True
    age = raw.get("age")
    return isinstance(age, int) and age < _ADULT_AGE


def strip_passengers(raw_passengers: list[dict[str, Any]]) -> tuple[list[PassengerView], bool]:
    """Return the sanitized passenger views and whether the party has a minor."""
    views = [to_passenger_view(p) for p in raw_passengers]
    return views, any(is_minor(p) for p in raw_passengers)
