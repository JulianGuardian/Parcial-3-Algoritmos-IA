import pytest

from app.disruption.assessment.sources import get_trip_context
from app.disruption.contracts import BookingNotFound, ToolUnavailable
from app.disruption.entitlements.sources import get_eligible_options, get_policy_rules


def test_policy_rules_have_contract_shape():
    policy = get_policy_rules("DELAY")

    assert policy["version"] == "POL-DELAY-2026-03"
    assert [r["rule_id"] for r in policy["rules"]] == ["R1", "R2", "R3", "R4", "R5"]
    for rule in policy["rules"]:
        assert {"rule_id", "condition", "entitlement", "requires_human_approval"} <= set(rule)
    assert policy["_meta"]["superseded_versions"] == ["POL-DELAY-2025-11"]


def test_unknown_scenario_is_a_tool_failure():
    with pytest.raises(ToolUnavailable):
        get_policy_rules("WEATHER")


def test_eligible_options_have_contract_shape():
    options = get_eligible_options(get_trip_context("ABC123"))

    assert [o["option_id"] for o in options["options"]] == ["O1", "O2", "O3"]
    assert options["_meta"] == {"retrieved_at": "2026-09-15T11:02:35Z", "ttl_seconds": 120}
    assert {"flight_number", "fare_difference", "seats_available", "confidence"} <= set(options["options"][0])


def test_options_for_unknown_booking():
    with pytest.raises(BookingNotFound):
        get_eligible_options({"booking_id": "NOPE99"})
