from app.disruption.actions.service import idempotency_key
from app.disruption.actions.write_tools import HUMAN_CASE, REBOOKING, MockWriteTools
from app.disruption.agents.contracts import STATE_HUMAN_CASE, STATE_REBOOKING, STATE_TOOL_LOG
from app.disruption.agents.guardrails import enforce_escalation, make_before_tool_callback

from .agent_helpers import FakeToolContext, session, tool, toolkit


def run_rebooking(state, writes=None):
    """Simulate ADK: callback first; the tool runs only if the callback returns None."""
    writes = writes or MockWriteTools()
    deps, tools = toolkit(writes)
    ctx = FakeToolContext(state)
    callback = make_before_tool_callback(deps)
    blocked = callback(tool("request_rebooking"), {"option_id": "O1"}, ctx)
    result = blocked if blocked is not None else tools["request_rebooking"]("O1", ctx)
    return result, writes, ctx


def test_rebooking_blocked_without_confirmation():
    result, writes, _ = run_rebooking(session("DEF456"))

    assert result["blocked_reason"] == "NOT_CONFIRMED"
    assert writes.calls_to(REBOOKING) == []


def test_rebooking_blocked_when_confirmed_option_has_expired():
    result, writes, _ = run_rebooking(session("DEF456", confirmed="O1", now="2026-09-15T12:00:00Z"))

    assert result["blocked_reason"] == "OPTION_NOT_VALID"
    assert writes.calls_to(REBOOKING) == []


def test_rebooking_blocked_when_a_human_is_required():
    result, writes, _ = run_rebooking(session("ABC123", confirmed="O1"))

    assert result["blocked_reason"] == "HUMAN_REQUIRED"
    assert writes.calls_to(REBOOKING) == []


def test_rebooking_blocked_for_an_option_other_than_the_confirmed_one():
    deps, _ = toolkit()
    callback = make_before_tool_callback(deps)

    result = callback(tool("request_rebooking"), {"option_id": "O2"}, FakeToolContext(session("DEF456", confirmed="O1")))

    assert result["blocked_reason"] == "NOT_CONFIRMED"


def test_confirmed_and_valid_option_makes_exactly_one_rebooking():
    result, writes, ctx = run_rebooking(session("DEF456", confirmed="O1"))

    [call] = writes.calls_to(REBOOKING)
    assert call.arguments["idempotency_key"] == idempotency_key("DEF456", "O1", "POL-DELAY-2026-03")
    assert result["status"] == "PENDING" and result["request_id"] == "RBK-88231"
    assert ctx.state[STATE_REBOOKING]["status"] == "PENDING"


def test_two_timeouts_stay_indeterminate_and_enforcement_escalates():
    writes = MockWriteTools(rebooking_statuses=[503, 503])
    result, writes, ctx = run_rebooking(session("DEF456", confirmed="O1"), writes)
    deps, _ = toolkit(writes)

    case = enforce_escalation(ctx.state, deps)

    assert result["status"] == "INDETERMINATE"
    assert len(writes.calls_to(REBOOKING)) == 2
    assert case.reasons == ["REBOOKING_INDETERMINATE"]
    assert case.enforced_by_code is True


def test_invalid_escalation_reason_is_blocked_by_callback():
    deps, _ = toolkit()
    callback = make_before_tool_callback(deps)

    result = callback(tool("escalate_to_human"), {"reason": "approve refund"}, FakeToolContext(session()))

    assert result["error"] == "INVALID_ARGUMENT"


def test_unknown_tool_is_refused():
    deps, _ = toolkit()
    callback = make_before_tool_callback(deps)

    result = callback(tool("create_rebooking_request"), {}, FakeToolContext(session()))

    assert result == {"error": "UNKNOWN_TOOL", "tool": "create_rebooking_request"}


def test_read_tools_pass_through_the_callback():
    deps, _ = toolkit()
    callback = make_before_tool_callback(deps)

    assert callback(tool("get_entitlements"), {}, FakeToolContext(session())) is None


def test_escalation_enforced_when_the_agent_forgets_it():
    writes = MockWriteTools()
    deps, _ = toolkit(writes)
    state = session("ABC123")

    case = enforce_escalation(state, deps)
    again = enforce_escalation(state, deps)

    assert case.enforced_by_code is True
    assert "R5_PRIORITY_HANDLING" in case.reasons and "POLICY_REQUIRES_HUMAN" in case.reasons
    assert again == case
    assert len(writes.calls_to(HUMAN_CASE)) == 1
    assert state[STATE_TOOL_LOG][-1]["outcome"] == "enforced_by_code"


def test_enforcement_reuses_the_case_the_agent_opened():
    writes = MockWriteTools()
    deps, tools = toolkit(writes)
    ctx = FakeToolContext(session("ABC123"))
    tools["escalate_to_human"]("POLICY_REQUIRES_HUMAN", ctx)

    case = enforce_escalation(ctx.state, deps)

    assert case.enforced_by_code is False
    assert len(writes.calls_to(HUMAN_CASE)) == 1


def test_contradictory_sources_escalate_as_unresolved_data():
    deps, _ = toolkit()
    state = session("GHI789")

    case = enforce_escalation(state, deps)

    assert "UNRESOLVED_DATA" in case.reasons
    assert state[STATE_HUMAN_CASE]["case_id"] == "HC-4471"


def test_no_enforcement_when_nothing_requires_a_human():
    deps, _ = toolkit()

    assert enforce_escalation(session("DEF456"), deps) is None
