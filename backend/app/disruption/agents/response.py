"""Structured response of one agent turn (task 3.2, design D5).

Every field except `reply` is computed in code: it comes from the same
deterministic evaluation the tools return, plus the writes recorded in
session state. The model only drafts `reply`, and the draft is kept only if
it passes:
- the answer validator;
- the extra checks for this turn's actions: a human case exists, so the
  draft must mention an agent; no rebooking is pending, so it must not claim
  one.

Otherwise the template message is used.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.disruption.actions.service import ActionResult, HumanCase, RebookingOutcome, RebookingStatus
from app.disruption.agents.contracts import (
    STATE_HUMAN_CASE,
    STATE_REBOOKING,
    STATE_TOOL_LOG,
    AgentResponse,
    EntitlementOut,
    NextStep,
)
from app.disruption.agents.disruption_tools import Evaluation, ToolDeps, evaluate, option_view
from app.disruption.agents.validator import validate_answer_draft
from app.disruption.communication.messages import build_message, describe_what_happened
from app.disruption.contracts import AssessmentStatus

_PENDING = {RebookingStatus.PENDING.value, RebookingStatus.ALREADY_EXISTS.value}
_REBOOKING_CLAIMS = re.compile(
    r"\b(rebooked|has been (re)?booked|booking (is|was|has been) (confirmed|changed|updated)|"
    r"(your )?(new )?(flight|seat|rebooking) (is|has been) confirmed|we (have )?changed your booking)\b",
    re.IGNORECASE,
)


def build_response(
    state: Mapping[str, Any],
    deps: ToolDeps,
    *,
    reply_draft: str | None,
    degraded: bool = False,
    evaluation: Evaluation | None = None,
) -> AgentResponse:
    evaluation = evaluation or evaluate(state, deps)
    decision = evaluation.decision
    case = state.get(STATE_HUMAN_CASE) or None
    rebooking = state.get(STATE_REBOOKING) or None
    rebooking_status = rebooking["status"] if rebooking else None

    options = [option_view(decision.recommended_option)] if decision.recommended_option else []
    human_required = decision.requires_human or case is not None
    next_step = _next_step(evaluation, human_required, rebooking_status, bool(options))

    template = build_message(evaluation.trip, decision, _actions_from_state(case, rebooking)).text
    reply, fallback = _choose_reply(reply_draft, evaluation, human_required, rebooking_status, template)

    return AgentResponse(
        what_happened=describe_what_happened(evaluation.trip)
        if evaluation.trip.assessment_status not in (AssessmentStatus.CONFLICTING, AssessmentStatus.UNVERIFIED)
        else ["The latest status of the trip could not be verified."],
        entitlements=[
            EntitlementOut(rule_id=r.rule_id, entitlement=r.entitlement, policy_ref=decision.policy_ref or "")
            for r in decision.applied_rules
        ],
        options=options,
        next_step=next_step,
        policy_refs=[decision.policy_ref] if decision.policy_ref else [],
        human_required=human_required,
        human_case_id=case["case_id"] if case else None,
        rebooking_status=rebooking_status,
        reply=reply,
        reply_fallback=fallback,
        degraded=degraded,
        trajectory=[entry["tool"] for entry in state.get(STATE_TOOL_LOG) or []],
    )


def _next_step(evaluation: Evaluation, human_required: bool, rebooking_status: str | None, has_options: bool) -> NextStep:
    if rebooking_status in _PENDING:
        return NextStep.REBOOKING_PENDING
    if human_required or rebooking_status == RebookingStatus.INDETERMINATE.value:
        return NextStep.AGENT_WILL_CONTACT
    if has_options:
        return NextStep.CONFIRM_OPTION
    if not evaluation.trip.relevant:
        return NextStep.NO_ACTION_NEEDED
    return NextStep.VERIFYING


def _choose_reply(
    draft: str | None,
    evaluation: Evaluation,
    human_required: bool,
    rebooking_status: str | None,
    template: str,
) -> tuple[str, str | None]:
    if not draft or not draft.strip():
        return template, "no_draft"
    own_flights = {s.flight_number for s in evaluation.trip.segments}
    verdict = validate_answer_draft(draft, evaluation.decision, own_flights=own_flights)
    if not verdict.accepted:
        return template, verdict.reason
    lowered = draft.lower()
    if human_required and "agent" not in lowered and "human" not in lowered:
        return template, "contradicts_requires_human"
    if rebooking_status not in _PENDING and _REBOOKING_CLAIMS.search(draft):
        return template, "overclaims_rebooking"
    return draft, None


def _actions_from_state(case: dict | None, rebooking: dict | None) -> ActionResult:
    """Rebuild the action outcome the template message expects."""
    result = ActionResult()
    if rebooking:
        status = rebooking["status"]
        result.rebooking = RebookingOutcome(
            RebookingStatus(status) if status in RebookingStatus.__members__ else RebookingStatus.NOT_ATTEMPTED,
            request_id=rebooking.get("request_id"),
            expires_at=rebooking.get("expires_at"),
            attempts=rebooking.get("attempts", 0),
        )
    if case:
        result.human_case = HumanCase(
            case_id=case["case_id"], queue=case["queue"], sla_minutes=case["sla_minutes"], reasons=tuple(case["reasons"])
        )
    return result
