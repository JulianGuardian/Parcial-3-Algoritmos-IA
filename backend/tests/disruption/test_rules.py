import json
from dataclasses import asdict

import pytest

from app.disruption.contracts import ToolUnavailable
from app.disruption.entitlements.rules import (
    RuleContext,
    build_context,
    evaluate_condition,
    evaluate_rules,
)
from app.disruption.entitlements.sources import get_policy_rules


def ids(results):
    return [r.rule_id for r in results]


def context(**overrides):
    base = dict(
        delay_minutes=0,
        missed_connection=False,
        group_includes_minor=False,
        compensation_requested=False,
        international=False,
    )
    return RuleContext(**{**base, **overrides})


def test_abc123_applies_r3_and_r5_only(abc123_state):
    evaluation = evaluate_rules(get_policy_rules("DELAY"), build_context(abc123_state, compensation_requested=False))

    assert ids(evaluation.applied) == ["R3", "R5"]
    assert ids(evaluation.not_applied) == ["R1", "R2", "R4"]
    assert evaluation.policy_ref == "POL-DELAY-2026-03"


def test_reasons_are_recorded(abc123_state):
    evaluation = evaluate_rules(get_policy_rules("DELAY"), build_context(abc123_state, compensation_requested=False))
    reasons = {r.rule_id: r.reason for r in evaluation.applied + evaluation.not_applied}

    assert reasons["R1"] == "160 < 180"
    assert reasons["R2"] == "160 < 240"
    assert "compensation_requested is false" in reasons["R4"]
    assert "missed_connection" in reasons["R3"]
    assert "group_includes_minor" in reasons["R5"]


def test_entitlements_and_approval_flags_come_from_the_policy(abc123_state):
    evaluation = evaluate_rules(get_policy_rules("DELAY"), build_context(abc123_state, compensation_requested=False))
    by_id = {r.rule_id: r for r in evaluation.applied}

    assert by_id["R3"].entitlement == "REBOOK_NO_FEE" and not by_id["R3"].requires_human_approval
    assert by_id["R5"].entitlement == "PRIORITY_HANDLING" and by_id["R5"].requires_human_approval


def test_superseded_version_is_never_used(abc123_state):
    evaluation = evaluate_rules(get_policy_rules("DELAY"), build_context(abc123_state, compensation_requested=True))
    payload = json.dumps(asdict(evaluation))

    assert "POL-DELAY-2025-11" not in payload
    assert evaluation.policy_ref == "POL-DELAY-2026-03"


def test_compensation_request_applies_r4(abc123_state):
    evaluation = evaluate_rules(get_policy_rules("DELAY"), build_context(abc123_state, compensation_requested=True))

    assert ids(evaluation.applied) == ["R3", "R4", "R5"]


def test_r1_applies_at_the_threshold():
    assert evaluate_condition("delay_minutes >= 180", context(delay_minutes=180))[0] is True
    assert evaluate_condition("delay_minutes >= 180", context(delay_minutes=179))[0] is False


def test_r2_needs_both_terms():
    condition = "delay_minutes >= 240 AND international"
    assert evaluate_condition(condition, context(delay_minutes=300, international=True))[0] is True
    assert evaluate_condition(condition, context(delay_minutes=300, international=False)) == (False, "international is false", False)
    assert evaluate_condition(condition, context(delay_minutes=100, international=True))[1] == "100 < 240"


def test_unknown_airport_is_reported_not_guessed(abc123_state):
    state = abc123_state
    state.segments[0].origin = "ZZZ"
    state.segments[0].delay_minutes = 300  # reach the `international` term of R2
    evaluation = evaluate_rules(get_policy_rules("DELAY"), build_context(state, compensation_requested=False))

    assert "R2" in ids(evaluation.not_applied)
    assert evaluation.missing_inputs == ["airport_country:ZZZ"]


def test_conditions_are_parsed_not_evaluated():
    with pytest.raises(ToolUnavailable):
        evaluate_condition("__import__('os').system('x')", context())
    with pytest.raises(ToolUnavailable):
        evaluate_condition("seats_left >= 2", context())


def test_malformed_policy_is_a_tool_failure():
    with pytest.raises(ToolUnavailable):
        evaluate_rules({"rules": []}, context())
