"""Mock read adapters for the policy and eligible-options tools."""

from typing import Any

from app.disruption.contracts import BookingNotFound, ToolUnavailable
from app.disruption.fixtures import load_fixture

_POLICIES = {"DELAY": "get_policy_rules_DELAY"}
_OPTIONS_BY_BOOKING = {"ABC123": "get_eligible_options_ABC123"}


def get_policy_rules(scenario: str) -> dict[str, Any]:
    """`get_policy_rules(scenario)`: the current versioned rule set."""
    fixture = _POLICIES.get(scenario)
    if fixture is None:
        raise ToolUnavailable(f"no policy available for scenario {scenario!r}")
    return load_fixture(fixture)


def get_eligible_options(trip_context: dict[str, Any]) -> dict[str, Any]:
    """`get_eligible_options(trip_context)`: candidates only, not a final decision."""
    booking_id = trip_context.get("booking_id", "")
    fixture = _OPTIONS_BY_BOOKING.get(booking_id)
    if fixture is None:
        raise BookingNotFound(booking_id)
    return load_fixture(fixture)
