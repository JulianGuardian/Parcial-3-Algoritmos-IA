from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.disruption.actions.service import (
    REBOOKING_INDETERMINATE,
    RebookingStatus,
    execute_actions,
    idempotency_key,
)
from app.disruption.actions.write_tools import HUMAN_CASE, REBOOKING, MockWriteTools
from app.disruption.contracts import ResolveRequest
from app.disruption.entitlements.service import decide
from app.disruption.entitlements.sources import get_eligible_options, get_policy_rules

NOW = datetime(2026, 9, 15, 11, 3, 0, tzinfo=timezone.utc)


def decide_for(state, *, compensation_requested=False):
    return decide(
        state,
        policy=get_policy_rules("DELAY"),
        options_response=get_eligible_options({"booking_id": state.booking_id}),
        request=ResolveRequest(state.booking_id, compensation_requested=compensation_requested),
        now=NOW,
    )


@pytest.fixture
def abc123_decision(abc123_state):
    return decide_for(abc123_state)


@pytest.fixture
def auto_decision(abc123_decision):
    """ABC123 as if no human were needed, to exercise the rebooking path."""
    return replace(abc123_decision, requires_human=False, human_reasons=[], auto_deliverable=True)


def test_abc123_creates_a_human_case_and_no_rebooking(abc123_state, abc123_decision):
    tools = MockWriteTools()

    result = execute_actions(abc123_decision, abc123_state, tools)

    assert tools.calls_to(REBOOKING) == []
    assert result.rebooking.status is RebookingStatus.NOT_ATTEMPTED
    assert result.human_case.case_id == "HC-4471"
    assert result.human_case.reasons == ("R5_PRIORITY_HANDLING",)


def test_r4_and_r5_create_exactly_one_case_listing_both_reasons(abc123_state):
    decision = decide_for(abc123_state, compensation_requested=True)
    tools = MockWriteTools()

    result = execute_actions(decision, abc123_state, tools)

    [call] = tools.calls_to(HUMAN_CASE)
    assert set(result.human_case.reasons) == {"R4_CASH_COMPENSATION", "R5_PRIORITY_HANDLING"}
    assert set(call.arguments["evidence"]["human_reasons"]) == {"R4_CASH_COMPENSATION", "R5_PRIORITY_HANDLING"}


def test_human_case_evidence_is_complete_and_has_no_document_id(abc123_state, abc123_decision):
    tools = MockWriteTools()

    execute_actions(abc123_decision, abc123_state, tools)

    evidence = tools.calls_to(HUMAN_CASE)[0].arguments["evidence"]
    assert {r["rule_id"] for r in evidence["applied_rules"]} == {"R3", "R5"}
    assert evidence["recommended_option"]["option_id"] == "O1"
    assert {r["option_id"] for r in evidence["rejected_options"]} == {"O2", "O3"}
    assert "E-1012" in {e["event_id"] for e in evidence["discarded_events"]}
    assert "12.345.678-9" not in repr(evidence)
    assert "maria.silva@example.com" not in repr(evidence)


def test_same_decision_yields_same_key(auto_decision, abc123_state):
    first, second = MockWriteTools(), MockWriteTools()

    execute_actions(auto_decision, abc123_state, first)
    execute_actions(auto_decision, abc123_state, second)

    key_1 = first.calls_to(REBOOKING)[0].arguments["idempotency_key"]
    key_2 = second.calls_to(REBOOKING)[0].arguments["idempotency_key"]
    assert key_1 == key_2 == idempotency_key("ABC123", "O1", "POL-DELAY-2026-03")


def test_auto_rebooking_is_reported_as_pending_not_confirmed(auto_decision, abc123_state):
    result = execute_actions(auto_decision, abc123_state, MockWriteTools())

    assert result.rebooking.status is RebookingStatus.PENDING
    assert result.rebooking.request_id == "RBK-88231"
    assert result.rebooking.expires_at == "2026-09-15T11:12:00Z"
    assert result.human_case is None


def test_duplicate_request_reuses_existing_id(auto_decision, abc123_state):
    tools = MockWriteTools(rebooking_statuses=[409])

    result = execute_actions(auto_decision, abc123_state, tools)

    assert result.rebooking.status is RebookingStatus.ALREADY_EXISTS
    assert result.rebooking.request_id == "RBK-88231"
    assert len(tools.calls_to(REBOOKING)) == 1


def test_single_timeout_is_retried_with_the_same_key(auto_decision, abc123_state):
    tools = MockWriteTools(rebooking_statuses=[503])

    result = execute_actions(auto_decision, abc123_state, tools)

    calls = tools.calls_to(REBOOKING)
    assert len(calls) == 2
    assert calls[0].arguments["idempotency_key"] == calls[1].arguments["idempotency_key"]
    assert result.rebooking.status is RebookingStatus.PENDING
    assert result.human_case is None


def test_two_timeouts_make_exactly_two_calls_and_escalate(auto_decision, abc123_state):
    tools = MockWriteTools(rebooking_statuses=[503, 503])

    result = execute_actions(auto_decision, abc123_state, tools)

    assert len(tools.calls_to(REBOOKING)) == 2
    assert result.rebooking.status is RebookingStatus.INDETERMINATE
    assert result.human_case.reasons == (REBOOKING_INDETERMINATE,)
