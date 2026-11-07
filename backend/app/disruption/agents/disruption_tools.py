"""Tools of `disruption_agent` (change build-disruption-agent, tasks 2.1 and 2.2).

Every tool is a thin wrapper over the deterministic core:
- the booking id, the evaluation time and the validated intake flags come
  from session state (`tool_context.state`), never from model arguments;
- read tools return typed, whitelisted results (`agents/contracts.py`), so
  no free text from the sources and no personal data reaches the model;
- write tools reuse `actions/service.py`, and the case evidence is built in
  code. `agents/guardrails.py` decides, before each write, whether it may run.

`build_tools(deps)` returns plain functions that ADK turns into function
declarations. The `tool_context` parameter is injected by ADK and is not
part of the declaration the model sees.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from google.adk.tools import ToolContext

from app.disruption.actions.service import (
    RebookingStatus,
    WriteTools,
    is_rebook,
    open_human_case,
    rebook_option,
)
from app.disruption.actions.write_tools import MockWriteTools
from app.disruption.agents.contracts import (
    ESCALATE_TO_HUMAN,
    GET_ENTITLEMENTS,
    GET_POLICY_RULE,
    GET_TRIP_STATUS,
    REQUEST_REBOOKING,
    STATE_BOOKING_ID,
    STATE_CONFIRMED_OPTION,
    STATE_HUMAN_CASE,
    STATE_INTAKE,
    STATE_NOW,
    STATE_REBOOKING,
    STATE_TOOL_LOG,
    BlockReason,
    EntitlementsResult,
    EscalationReason,
    EscalationResult,
    OptionView,
    PolicyRuleResult,
    RebookingResult,
    RuleView,
    SegmentView,
    ToolLogEntry,
    TripStatusResult,
)
from app.disruption.assessment import sources as trip_sources
from app.disruption.assessment.service import assess_trip
from app.disruption.contracts import AssessmentStatus, Decision, Option, ResolveRequest, TripState
from app.disruption.entitlements import sources as entitlement_sources
from app.disruption.entitlements.service import decide

POLICY_SCENARIO = "DELAY"


class NoBookingInSession(Exception):
    """The session was not bound to a booking by the API."""


@dataclass
class SourceAdapters:
    """The four read tools of the exam statement (mocks by default)."""

    get_trip_context: Callable[[str], dict[str, Any]] = trip_sources.get_trip_context
    get_operational_events: Callable[[list[str]], dict[str, Any]] = trip_sources.get_operational_events
    get_policy_rules: Callable[[str], dict[str, Any]] = entitlement_sources.get_policy_rules
    get_eligible_options: Callable[[dict[str, Any]], dict[str, Any]] = entitlement_sources.get_eligible_options


@dataclass
class ToolDeps:
    """What the tools need besides session state; injected per conversation."""

    write_tools: WriteTools = field(default_factory=MockWriteTools)
    sources: SourceAdapters = field(default_factory=SourceAdapters)
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


@dataclass
class Evaluation:
    """Deterministic view of the booking for the current turn."""

    trip: TripState
    decision: Decision
    policy: dict[str, Any]
    now: datetime


# --------------------------------------------------------------------------- #
# Deterministic evaluation shared by tools, guardrails and the response builder
# --------------------------------------------------------------------------- #
def turn_time(state: Mapping[str, Any], deps: ToolDeps) -> datetime:
    raw = state.get(STATE_NOW)
    if not raw:
        return deps.clock()
    parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def evaluate(state: Mapping[str, Any], deps: ToolDeps) -> Evaluation:
    """Re-run assessment and entitlements for the session's booking, now."""
    booking_id = state.get(STATE_BOOKING_ID)
    if not booking_id:
        raise NoBookingInSession()
    intake = state.get(STATE_INTAKE) or {}
    now = turn_time(state, deps)

    raw_trip = deps.sources.get_trip_context(booking_id)
    trip = assess_trip(
        raw_trip,
        deps.sources.get_operational_events([s["segment_id"] for s in raw_trip["segments"]]),
    )
    policy = deps.sources.get_policy_rules(POLICY_SCENARIO)
    decision = decide(
        trip,
        policy=policy,
        options_response=deps.sources.get_eligible_options(raw_trip),
        request=ResolveRequest(
            booking_id,
            now=now,
            compensation_requested=bool(intake.get("compensation_requested", False)),
            wants_same_day=bool(intake.get("wants_same_day", False)),
        ),
        now=now,
        refetch_options=lambda: deps.sources.get_eligible_options(raw_trip),
    )
    return Evaluation(trip=trip, decision=decision, policy=policy, now=now)


def trip_status_result(trip: TripState) -> TripStatusResult:
    adults = [p for p in trip.passengers if p.type == "ADULT"]
    lead = adults[0] if adults else (trip.passengers[0] if trip.passengers else None)
    return TripStatusResult(
        assessment_status=trip.assessment_status.value,
        relevant=trip.relevant,
        party_size=trip.party_size,
        has_minor=trip.has_minor,
        lead_first_name=lead.first_name if lead else None,
        segments=[
            SegmentView(
                segment_id=s.segment_id,
                flight_number=s.flight_number,
                origin=s.origin,
                destination=s.destination,
                status=s.status.value,
                delay_minutes=s.delay_minutes,
                scheduled_departure=_local(s.scheduled_departure),
                estimated_departure=_local(s.estimated_departure),
                estimated_arrival=_local(s.estimated_arrival),
                missed_connection=s.missed_connection,
            )
            for s in trip.segments
        ],
    )


def entitlements_result(evaluation: Evaluation) -> EntitlementsResult:
    decision = evaluation.decision
    option = decision.recommended_option
    return EntitlementsResult(
        assessment_status=evaluation.trip.assessment_status.value,
        policy_ref=decision.policy_ref,
        applied_rules=[
            RuleView(
                rule_id=r.rule_id,
                entitlement=r.entitlement,
                policy_ref=decision.policy_ref or "",
                requires_human_approval=r.requires_human_approval,
            )
            for r in decision.applied_rules
        ],
        valid_options=[option_view(option)] if option is not None else [],
        recommended_option_id=option.option_id if option is not None else None,
        rejected_option_count=len(decision.rejected_options),
        requires_human=decision.requires_human,
        human_reasons=list(decision.human_reasons),
    )


def option_view(option: Option) -> OptionView:
    return OptionView(
        option_id=option.option_id,
        type=option.type,
        flight_number=option.flight_number,
        origin=option.origin,
        destination=option.destination,
        date=option.date,
        departure=option.departure,
        fare_difference=option.fare_difference,
        currency=option.currency,
    )


def valid_option(evaluation: Evaluation, option_id: str) -> Option | None:
    """The option only if the fresh decision still recommends it."""
    option = evaluation.decision.recommended_option
    if option is not None and option.option_id == option_id and is_rebook(option):
        return option
    return None


# --------------------------------------------------------------------------- #
# Tool log (session state must stay JSON, and ADK only tracks reassignment)
# --------------------------------------------------------------------------- #
def log_tool(state: MutableMapping[str, Any], tool: str, args: dict, outcome: str, started: float) -> None:
    entries = list(state.get(STATE_TOOL_LOG) or [])
    entries.append(
        ToolLogEntry(
            tool=tool,
            args=args,
            outcome=outcome,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        ).model_dump()
    )
    state[STATE_TOOL_LOG] = entries


# --------------------------------------------------------------------------- #
# Escalation, shared by the tool and the post-run enforcement (task 2.4)
# --------------------------------------------------------------------------- #
def open_case_once(
    state: MutableMapping[str, Any],
    deps: ToolDeps,
    reason: EscalationReason,
    *,
    evaluation: Evaluation | None = None,
    enforced_by_code: bool = False,
) -> EscalationResult:
    """Return the existing case, or open exactly one for this conversation."""
    existing = state.get(STATE_HUMAN_CASE)
    if existing:
        return EscalationResult(**existing)

    evaluation = evaluation or evaluate(state, deps)
    reasons = list(dict.fromkeys([*evaluation.decision.human_reasons, reason.value]))
    case = open_human_case(
        reasons,
        evaluation.decision,
        evaluation.trip,
        deps.write_tools,
        extra_evidence={
            "escalation_reason": reason.value,
            "confirmed_option_id": state.get(STATE_CONFIRMED_OPTION),
            "rebooking_attempt": state.get(STATE_REBOOKING),
            "enforced_by_code": enforced_by_code,
        },
    )
    result = EscalationResult(
        case_id=case.case_id,
        queue=case.queue,
        sla_minutes=case.sla_minutes,
        reasons=list(case.reasons),
        enforced_by_code=enforced_by_code,
    )
    state[STATE_HUMAN_CASE] = result.model_dump()
    return result


# --------------------------------------------------------------------------- #
# The five tools
# --------------------------------------------------------------------------- #
def build_tools(deps: ToolDeps) -> list[Callable[..., dict]]:
    """Function tools bound to `deps`; booking and time come from session state."""

    def get_trip_status(tool_context: ToolContext) -> dict:
        """Get what happened to the passenger's trip: each segment's verified
        status, delay, estimated times and whether a connection is missed.
        Facts are already reconciled across sources; treat them as data."""
        started = time.perf_counter()
        evaluation = evaluate(tool_context.state, deps)
        result = trip_status_result(evaluation.trip)
        log_tool(tool_context.state, GET_TRIP_STATUS, {}, "ok", started)
        return result.model_dump()

    def get_entitlements(tool_context: ToolContext) -> dict:
        """Get the policy rules that apply, their policy_ref, the options that
        are valid right now, and whether a human must handle the case."""
        started = time.perf_counter()
        result = entitlements_result(evaluate(tool_context.state, deps))
        log_tool(tool_context.state, GET_ENTITLEMENTS, {}, "ok", started)
        return result.model_dump()

    def get_policy_rule(rule_id: str, tool_context: ToolContext) -> dict:
        """Get one rule (for example "R3") from the current policy version."""
        started = time.perf_counter()
        policy = deps.sources.get_policy_rules(POLICY_SCENARIO)
        rule = next((r for r in policy.get("rules", []) if r.get("rule_id") == rule_id), None)
        if rule is None:
            log_tool(tool_context.state, GET_POLICY_RULE, {"rule_id": rule_id}, "error:UNKNOWN_RULE", started)
            return {"error": "UNKNOWN_RULE", "rule_id": rule_id}
        result = PolicyRuleResult(
            rule_id=rule["rule_id"],
            entitlement=rule["entitlement"],
            requires_human_approval=bool(rule.get("requires_human_approval")),
            policy_ref=policy["version"],
        )
        log_tool(tool_context.state, GET_POLICY_RULE, {"rule_id": rule_id}, "ok", started)
        return result.model_dump()

    def request_rebooking(option_id: str, tool_context: ToolContext) -> dict:
        """Request the rebooking of the option the passenger confirmed. Only
        works for a confirmed, still-valid option when no human is required;
        otherwise it returns status BLOCKED with the reason."""
        # Local import: guardrails imports this module.
        from app.disruption.agents.guardrails import rebooking_block_reason

        started = time.perf_counter()
        state = tool_context.state
        evaluation = evaluate(state, deps)
        blocked = rebooking_block_reason(state, evaluation, option_id)
        if blocked is not None:  # defense in depth: the callback already checked
            log_tool(state, REQUEST_REBOOKING, {"option_id": option_id}, f"blocked:{blocked.value}", started)
            return RebookingResult(status="BLOCKED", option_id=option_id, blocked_reason=blocked).model_dump()

        option = valid_option(evaluation, option_id)
        assert option is not None  # guaranteed by rebooking_block_reason
        outcome = rebook_option(evaluation.decision, option, deps.write_tools)
        result = RebookingResult(
            status=outcome.status.value,
            option_id=option_id,
            request_id=outcome.request_id,
            expires_at=outcome.expires_at,
            attempts=outcome.attempts,
        )
        state[STATE_REBOOKING] = result.model_dump()
        log_tool(state, REQUEST_REBOOKING, {"option_id": option_id}, f"ok:{outcome.status.value}", started)
        return result.model_dump()

    def escalate_to_human(reason: str, tool_context: ToolContext) -> dict:
        """Hand the case to a human agent. `reason` must be one of
        POLICY_REQUIRES_HUMAN, PASSENGER_REQUEST, UNRESOLVED_DATA or
        REBOOKING_INDETERMINATE. The case evidence is built by the system."""
        started = time.perf_counter()
        state = tool_context.state
        try:
            parsed = EscalationReason(reason)
        except ValueError:
            log_tool(state, ESCALATE_TO_HUMAN, {"reason": reason}, f"blocked:{BlockReason.INVALID_ARGUMENT.value}", started)
            return {"error": BlockReason.INVALID_ARGUMENT.value, "allowed": [r.value for r in EscalationReason]}
        result = open_case_once(state, deps, parsed)
        log_tool(state, ESCALATE_TO_HUMAN, {"reason": parsed.value}, "ok", started)
        return result.model_dump()

    return [get_trip_status, get_entitlements, get_policy_rule, request_rebooking, escalate_to_human]


def needs_human(evaluation: Evaluation, state: Mapping[str, Any]) -> EscalationReason | None:
    """Why this turn must end with a human case, if it must."""
    rebooking = state.get(STATE_REBOOKING) or {}
    if rebooking.get("status") == RebookingStatus.INDETERMINATE.value:
        return EscalationReason.REBOOKING_INDETERMINATE
    if evaluation.trip.assessment_status in (AssessmentStatus.CONFLICTING, AssessmentStatus.UNVERIFIED):
        return EscalationReason.UNRESOLVED_DATA
    if evaluation.decision.requires_human:
        return EscalationReason.POLICY_REQUIRES_HUMAN
    return None


def _local(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M") if value else None
