"""Code-level guardrails for the agent's tools (tasks 2.3 and 2.4).

Spec `agent-tool-guardrails`. These checks run in code, outside the prompt:
- `make_before_tool_callback` blocks a write before ADK executes it:
  - rebooking needs a confirmed option that is still valid, with no human
    required;
  - escalation needs a reason from the closed set;
  - any tool outside the allowed set is refused.
- `enforce_escalation` runs after the agent finishes: if the turn must end
  with a human case and the model did not open one, the code opens it.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, MutableMapping
from typing import Any

from app.disruption.agents.contracts import (
    ESCALATE_TO_HUMAN,
    READ_TOOLS,
    REQUEST_REBOOKING,
    STATE_CONFIRMED_OPTION,
    STATE_HUMAN_CASE,
    WRITE_TOOLS,
    BlockReason,
    EscalationReason,
    EscalationResult,
    RebookingResult,
)
from app.disruption.agents.disruption_tools import (
    Evaluation,
    NoBookingInSession,
    ToolDeps,
    evaluate,
    log_tool,
    needs_human,
    open_case_once,
    valid_option,
)


def rebooking_block_reason(
    state: Mapping[str, Any], evaluation: Evaluation, option_id: str
) -> BlockReason | None:
    """None when the rebooking may run, otherwise the first rule it breaks."""
    if evaluation.decision.requires_human:
        return BlockReason.HUMAN_REQUIRED
    if state.get(STATE_CONFIRMED_OPTION) != option_id:
        return BlockReason.NOT_CONFIRMED
    if valid_option(evaluation, option_id) is None:
        return BlockReason.OPTION_NOT_VALID
    return None


def make_before_tool_callback(deps: ToolDeps) -> Callable[[Any, dict[str, Any], Any], dict | None]:
    """ADK `before_tool_callback`: return a dict to skip the tool, None to run it."""

    def before_tool_callback(tool: Any, args: dict[str, Any], tool_context: Any) -> dict | None:
        name = getattr(tool, "name", str(tool))
        state = tool_context.state
        started = time.perf_counter()

        if name not in READ_TOOLS | WRITE_TOOLS:
            log_tool(state, name, dict(args), "blocked:UNKNOWN_TOOL", started)
            return {"error": "UNKNOWN_TOOL", "tool": name}

        if name == ESCALATE_TO_HUMAN:
            reason = str(args.get("reason", ""))
            if reason not in EscalationReason.__members__:
                log_tool(state, name, {"reason": reason}, f"blocked:{BlockReason.INVALID_ARGUMENT.value}", started)
                return {"error": BlockReason.INVALID_ARGUMENT.value, "allowed": [r.value for r in EscalationReason]}
            return None

        if name == REQUEST_REBOOKING:
            option_id = str(args.get("option_id", ""))
            try:
                evaluation = evaluate(state, deps)
            except NoBookingInSession:
                blocked = BlockReason.NO_BOOKING
            else:
                blocked = rebooking_block_reason(state, evaluation, option_id)
            if blocked is not None:
                log_tool(state, name, {"option_id": option_id}, f"blocked:{blocked.value}", started)
                return RebookingResult(status="BLOCKED", option_id=option_id, blocked_reason=blocked).model_dump()
        return None

    return before_tool_callback


def enforce_escalation(state: MutableMapping[str, Any], deps: ToolDeps) -> EscalationResult | None:
    """After the run: guarantee exactly one human case when the turn needs one."""
    started = time.perf_counter()
    evaluation = evaluate(state, deps)
    reason = needs_human(evaluation, state)
    if reason is None:
        return None
    if state.get(STATE_HUMAN_CASE):
        return EscalationResult(**state[STATE_HUMAN_CASE])
    result = open_case_once(state, deps, reason, evaluation=evaluation, enforced_by_code=True)
    log_tool(state, ESCALATE_TO_HUMAN, {"reason": reason.value}, "enforced_by_code", started)
    return result
