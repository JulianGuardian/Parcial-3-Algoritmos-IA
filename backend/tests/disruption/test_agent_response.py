from app.disruption.actions.write_tools import MockWriteTools
from app.disruption.agents.contracts import (
    AgentResponse,
    EntitlementOut,
    EntitlementsResult,
    NextStep,
    TripStatusResult,
)
from app.disruption.agents.faithfulness import check_faithfulness
from app.disruption.agents.guardrails import enforce_escalation, make_before_tool_callback
from app.disruption.agents.response import build_response

from .agent_helpers import PII, FakeToolContext, session, tool, toolkit

GOOD_DRAFT = (
    "Your flight NB500 is delayed 160 minutes and you will miss NB2410. We can offer NB2412 on "
    "2026-09-16 at 08:15 at no extra cost. An agent will confirm it with you. Policy POL-DELAY-2026-03."
)


def abc123_turn(draft=GOOD_DRAFT, **session_kwargs):
    deps, tools = toolkit()
    ctx = FakeToolContext(session(**session_kwargs))
    tools["get_trip_status"](ctx)
    tools["get_entitlements"](ctx)
    tools["escalate_to_human"]("POLICY_REQUIRES_HUMAN", ctx)
    return build_response(ctx.state, deps, reply_draft=draft), ctx, tools


def test_abc123_structured_fields():
    response, _, _ = abc123_turn()

    assert {(e.rule_id, e.entitlement, e.policy_ref) for e in response.entitlements} == {
        ("R3", "REBOOK_NO_FEE", "POL-DELAY-2026-03"),
        ("R5", "PRIORITY_HANDLING", "POL-DELAY-2026-03"),
    }
    assert [o.option_id for o in response.options] == ["O1"]
    assert response.policy_refs == ["POL-DELAY-2026-03"]
    assert response.human_required is True
    assert response.human_case_id == "HC-4471"
    assert response.next_step is NextStep.AGENT_WILL_CONTACT
    assert response.trajectory == ["get_trip_status", "get_entitlements", "escalate_to_human"]
    assert any("delayed by 160 minutes" in line for line in response.what_happened)
    assert response.reply == GOOD_DRAFT and response.reply_fallback is None


def test_reply_mentioning_rejected_option_falls_back_to_template():
    response, _, _ = abc123_turn("Good news: you can take NB2450 tonight. An agent will help. POL-DELAY-2026-03")

    assert response.reply_fallback == "mentions_other_option"
    assert "NB2450" not in response.reply
    assert "POL-DELAY-2026-03" in response.reply


def test_reply_that_ignores_the_human_case_falls_back():
    response, _, _ = abc123_turn("We can offer NB2412 on 2026-09-16. POL-DELAY-2026-03")

    assert response.reply_fallback == "contradicts_requires_human"


def test_missing_draft_uses_template_and_is_flagged():
    deps, _ = toolkit()
    state = session("ABC123")
    enforce_escalation(state, deps)

    response = build_response(state, deps, reply_draft=None, degraded=True)

    assert response.degraded is True
    assert response.reply_fallback == "no_draft"
    assert response.human_case_id == "HC-4471"
    assert response.trajectory == ["escalate_to_human"]


def test_def456_without_confirmation_asks_to_confirm():
    deps, _ = toolkit()

    response = build_response(session("DEF456"), deps, reply_draft=None)

    assert response.next_step is NextStep.CONFIRM_OPTION
    assert response.human_required is False
    assert "Please confirm this option" in response.reply


def test_failed_write_never_claims_a_rebooking():
    writes = MockWriteTools(rebooking_statuses=[503, 503])
    deps, tools = toolkit(writes)
    ctx = FakeToolContext(session("DEF456", confirmed="O1"))
    callback = make_before_tool_callback(deps)
    assert callback(tool("request_rebooking"), {"option_id": "O1"}, ctx) is None
    tools["request_rebooking"]("O1", ctx)
    enforce_escalation(ctx.state, deps)

    response = build_response(
        ctx.state, deps, reply_draft="Done! You have been rebooked on NB2412. An agent may follow up. POL-DELAY-2026-03"
    )

    assert response.rebooking_status == "INDETERMINATE"
    assert response.next_step is NextStep.AGENT_WILL_CONTACT
    assert response.human_required is True
    assert response.reply_fallback == "overclaims_rebooking"
    assert "rebooked" not in response.reply.lower()


def test_contradictory_sources_have_no_options():
    deps, _ = toolkit()
    state = session("GHI789")
    enforce_escalation(state, deps)

    response = build_response(state, deps, reply_draft=None)

    assert response.options == []
    assert response.next_step is NextStep.AGENT_WILL_CONTACT
    assert response.what_happened == ["The latest status of the trip could not be verified."]


def test_response_contains_no_personal_data():
    response, _, _ = abc123_turn()

    dumped = response.model_dump_json()
    for leaked in PII:
        assert leaked not in dumped


def test_faithfulness_passes_for_the_abc123_response():
    response, ctx, tools = abc123_turn()
    entitlements = EntitlementsResult(**tools["get_entitlements"](ctx))
    trip = TripStatusResult(**tools["get_trip_status"](ctx))

    assert check_faithfulness(response, entitlements, trip).ok


def test_faithfulness_fails_on_unbacked_entitlement_and_flight():
    response, ctx, tools = abc123_turn()
    entitlements = EntitlementsResult(**tools["get_entitlements"](ctx))
    tampered = AgentResponse(
        **{
            **response.model_dump(),
            "entitlements": [
                *response.model_dump()["entitlements"],
                EntitlementOut(rule_id="R2", entitlement="MEAL_VOUCHER", policy_ref="POL-DELAY-2026-03").model_dump(),
            ],
            "reply": "Take NB2450 tonight.",
        }
    )

    result = check_faithfulness(tampered, entitlements)

    assert not result.ok
    assert "unbacked entitlement MEAL_VOUCHER (R2, POL-DELAY-2026-03)" in result.problems
    assert "reply mentions flight NB2450 outside options" in result.problems
