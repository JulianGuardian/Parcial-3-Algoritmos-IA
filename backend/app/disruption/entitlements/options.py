"""Option filtering (design D6) and recommendation.

Checks run in this order: TTL, seats, policy consistency, confidence and
evaluated policy. Every failing check is recorded as a reason code, with the
first one being the primary reason. `get_eligible_options` only returns
candidates, so nothing is offered until it passes all of them.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.disruption.assessment.freshness import ensure_utc, parse_utc
from app.disruption.contracts import FareConditions, Option, RejectedOption, RejectionReason

NO_FEE_ENTITLEMENT = "REBOOK_NO_FEE"
REBOOK_ENTITLEMENTS = frozenset({NO_FEE_ENTITLEMENT})
_CONFIDENCE_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


@dataclass
class OptionFilterResult:
    valid: list[Option] = field(default_factory=list)
    rejected: list[RejectedOption] = field(default_factory=list)
    expired: bool = False


def parse_option(raw: dict[str, Any]) -> Option:
    return Option(
        option_id=raw["option_id"],
        type=raw["type"],
        policy_ref=raw.get("policy_ref"),
        confidence=raw.get("confidence"),
        flight_number=raw.get("flight_number"),
        origin=raw.get("origin"),
        destination=raw.get("destination"),
        date=raw.get("date"),
        departure=raw.get("departure"),
        fare_difference=raw.get("fare_difference"),
        currency=raw.get("currency"),
        seats_available=raw.get("seats_available"),
    )


def options_expired(options_response: dict[str, Any], now: datetime) -> bool:
    """True when `retrieved_at + ttl_seconds` is earlier than `now`."""
    meta = options_response["_meta"]
    expires = parse_utc(meta["retrieved_at"]) + timedelta(seconds=int(meta["ttl_seconds"]))
    return expires < ensure_utc(now)


Failure = tuple[RejectionReason, str]


def _seat_failures(option: Option, party_size: int) -> list[Failure]:
    if option.type != "REBOOK" or option.seats_available is None:
        return []
    if option.seats_available >= party_size:
        return []
    return [
        (
            RejectionReason.INSUFFICIENT_SEATS,
            f"{option.seats_available} seat(s) for {party_size} passenger(s)",
        )
    ]


def _consistency_failures(option: Option, entitlements: set[str]) -> list[Failure]:
    if option.type != "REBOOK":
        return []
    if not entitlements & REBOOK_ENTITLEMENTS:
        return [(RejectionReason.POLICY_INCONSISTENT, "no rebooking entitlement applies")]
    if NO_FEE_ENTITLEMENT in entitlements and option.fare_difference not in (0, None):
        cost = f"{option.fare_difference} {option.currency}" if option.currency else str(option.fare_difference)
        return [(RejectionReason.POLICY_INCONSISTENT, f"fare_difference {cost} under {NO_FEE_ENTITLEMENT}")]
    return []


def _review_failures(option: Option, policy_ref: str, fare: FareConditions) -> list[Failure]:
    review = RejectionReason.REQUIRES_AGENT_REVIEW
    failures: list[Failure] = []
    if option.confidence == "LOW":
        note = "LOW confidence"
        if option.type == "REFUND" and fare.refundable is False:
            note += " on a non-refundable fare"
        failures.append((review, note))
    if option.policy_ref != policy_ref:
        failures.append((review, f"policy {option.policy_ref} was not retrieved or evaluated"))
    if option.type == "REBOOK" and (option.seats_available is None or option.fare_difference is None):
        failures.append((review, "seats or fare difference missing"))
    return failures


def filter_options(
    options_response: dict[str, Any],
    *,
    now: datetime,
    party_size: int,
    entitlements: set[str],
    policy_ref: str,
    fare: FareConditions,
) -> OptionFilterResult:
    options = [parse_option(raw) for raw in options_response.get("options", [])]
    result = OptionFilterResult()

    if options_expired(options_response, now):
        result.expired = True
        result.rejected = [
            RejectedOption(o.option_id, (RejectionReason.EXPIRED,), "options are past their TTL")
            for o in options
        ]
        return result

    for option in options:
        # Design D6 order: seats, policy consistency, confidence / evaluated policy.
        failures = (
            _seat_failures(option, party_size)
            + _consistency_failures(option, entitlements)
            + _review_failures(option, policy_ref, fare)
        )
        if failures:
            reasons = tuple(dict.fromkeys(reason for reason, _ in failures))
            detail = "; ".join(text for _, text in failures)
            result.rejected.append(RejectedOption(option.option_id, reasons, detail))
        else:
            result.valid.append(option)
    return result


def recommend(valid: list[Option]) -> Option | None:
    """No-cost rebooking, highest confidence first, then earliest departure."""
    candidates = [o for o in valid if o.type == "REBOOK" and o.fare_difference == 0]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda o: (_CONFIDENCE_RANK.get(o.confidence or "", 3), o.date or "", o.departure or ""),
    )
