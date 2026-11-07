"""End-to-end resolution of a disruption (design D2, D11, D12, D13).

intake (AI-assisted) -> assessment -> entitlements -> controlled actions ->
answer agent (AI-assisted, only when a question was asked) -> communication.

Every step except the two AI-assisted ones is deterministic. Read-tool
failures surface as `BookingNotFound` or `ToolUnavailable`, which the HTTP
layer maps to 404 and 503. A classifier or answer-agent failure never fails
the request: both degrade to a safe, deterministic fallback (task 4.4, 6.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.disruption.actions.service import ActionResult, WriteTools, execute_actions
from app.disruption.actions.write_tools import MockWriteTools
from app.disruption.agents.answer_agent import answer_question
from app.disruption.assessment.service import assess_trip
from app.disruption.assessment.sources import get_operational_events, get_trip_context
from app.disruption.communication.messages import Delivery, PassengerMessage, build_message, deliver
from app.disruption.contracts import Decision, ResolveRequest, TraceEntry, TripState
from app.disruption.entitlements.service import decide
from app.disruption.entitlements.sources import get_eligible_options, get_policy_rules
from app.disruption.intake.service import classify_question

POLICY_SCENARIO = "DELAY"


@dataclass
class Resolution:
    request: ResolveRequest
    evaluated_at: datetime
    state: TripState
    decision: Decision
    actions: ActionResult
    message: PassengerMessage
    delivery: Delivery
    trace: list[TraceEntry] = field(default_factory=list)


def resolve_disruption(
    request: ResolveRequest,
    *,
    write_tools: WriteTools | None = None,
    settings: Settings | None = None,
) -> Resolution:
    now = request.now or datetime.now(timezone.utc)
    tools = write_tools if write_tools is not None else MockWriteTools()
    settings = settings or get_settings()
    trace: list[TraceEntry] = []

    # Intake (design D11/D12): classify the free-text question, if any, into
    # a closed intent set. The classifier never decides entitlements; it can
    # only set the two flags `decide()` already accepts.
    intake = classify_question(
        request.question,
        classifier_backend=settings.intent_classifier,
        adk_model=settings.intent_model,
        adk_api_key=settings.intent_model_api_key,
    )
    effective_request = request
    if intake is not None:
        trace.append(intake.trace)
        if intake.intent_result.compensation_requested and not request.compensation_requested:
            effective_request = ResolveRequest(
                booking_id=request.booking_id,
                now=request.now,
                question=request.question,
                compensation_requested=True,
                wants_same_day=request.wants_same_day or intake.intent_result.wants_same_day,
            )

    trip = get_trip_context(request.booking_id)
    events = get_operational_events([s["segment_id"] for s in trip["segments"]])
    state = assess_trip(trip, events)

    decision = decide(
        state,
        policy=get_policy_rules(POLICY_SCENARIO),
        options_response=get_eligible_options(trip),
        request=effective_request,
        now=now,
        refetch_options=lambda: get_eligible_options(trip),
    )

    actions = execute_actions(decision, state, tools)
    message = build_message(state, decision, actions)

    # Answer agent (design D13): only runs when a question was asked. Its
    # draft always goes through the deterministic validator before it can
    # replace the template message; any failure keeps the template.
    if request.question:
        answer = answer_question(
            request.question,
            state,
            decision,
            model=settings.intent_model,
            api_key=settings.intent_model_api_key,
            fallback_message=message.text,
        )
        trace.append(answer.trace)
        message = PassengerMessage(
            text=answer.message,
            policy_ref=message.policy_ref,
            agent_follow_up=message.agent_follow_up,
        )

    delivery = deliver(message, tools)

    trace = [*trace, *state.trace, *decision.trace, *actions.trace, *delivery.trace]
    return Resolution(
        request=request,
        evaluated_at=now,
        state=state,
        decision=decision,
        actions=actions,
        message=message,
        delivery=delivery,
        trace=trace,
    )
