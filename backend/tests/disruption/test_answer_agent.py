from datetime import datetime, timezone

from app.disruption.agents.answer_agent import answer_question
from app.disruption.assessment.service import assess_trip
from app.disruption.assessment.sources import get_operational_events, get_trip_context
from app.disruption.contracts import ResolveRequest
from app.disruption.entitlements.service import decide
from app.disruption.entitlements.sources import get_eligible_options, get_policy_rules

NOW = datetime(2026, 9, 15, 11, 3, 0, tzinfo=timezone.utc)


class FakeAgentRunner:
    def __init__(self, draft_text=None, raise_exc=None):
        self.draft_text = draft_text
        self.raise_exc = raise_exc

    def draft(self, question, recorder):
        recorder.calls.append({"tool": "get_trip_summary", "args": {}, "latency_ms": 1.0})
        recorder.calls.append({"tool": "get_entitlements", "args": {}, "latency_ms": 1.0})
        if self.raise_exc:
            raise self.raise_exc
        return self.draft_text


def _trip_and_decision():
    trip = assess_trip(get_trip_context("ABC123"), get_operational_events(["S1", "S2"]))
    decision = decide(
        trip,
        policy=get_policy_rules("DELAY"),
        options_response=get_eligible_options({"booking_id": trip.booking_id}),
        request=ResolveRequest(trip.booking_id),
        now=NOW,
    )
    return trip, decision


def test_invalid_draft_sends_template():
    trip, decision = _trip_and_decision()
    runner = FakeAgentRunner(draft_text="You can take NB2450 tonight instead.")

    result = answer_question(
        "What are my options?",
        trip,
        decision,
        model="gemini-2.0-flash",
        api_key=None,
        agent_runner=runner,
    )

    assert result.fallback_used is True
    assert "NB2450" not in result.message
    assert decision.policy_ref in result.message


def test_timeout_sends_template_and_human_case_still_required():
    trip, decision = _trip_and_decision()
    runner = FakeAgentRunner(raise_exc=TimeoutError("timed out"))

    result = answer_question(
        "What are my options?",
        trip,
        decision,
        model="gemini-2.0-flash",
        api_key=None,
        agent_runner=runner,
    )

    assert result.fallback_used is True
    # Escalation is decided by the deterministic pipeline, not the agent:
    # requires_human is unaffected by the agent's failure.
    assert decision.requires_human is True
    assert decision.policy_ref in result.message


def test_valid_draft_is_sent_and_tool_calls_recorded():
    trip, decision = _trip_and_decision()
    recommended_flight = decision.recommended_option.flight_number
    draft = (
        f"We can offer {recommended_flight} under {decision.policy_ref}. "
        "An agent will confirm this with you shortly."
    )
    runner = FakeAgentRunner(draft_text=draft)

    result = answer_question(
        "What are my options?",
        trip,
        decision,
        model="gemini-2.0-flash",
        api_key=None,
        agent_runner=runner,
    )

    assert result.fallback_used is False
    assert result.message == draft
    assert len(result.trace.data["tool_calls"]) == 2
