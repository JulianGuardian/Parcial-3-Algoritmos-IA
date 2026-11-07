"""End-to-end resolution of a disruption (design D2 and D11).

assessment -> entitlements -> controlled actions -> passenger message.
Every step is deterministic. Read-tool failures surface as `BookingNotFound`
or `ToolUnavailable`, which the HTTP layer maps to 404 and 503.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.disruption.actions.service import ActionResult, WriteTools, execute_actions
from app.disruption.actions.write_tools import MockWriteTools
from app.disruption.assessment.service import assess_trip
from app.disruption.assessment.sources import get_operational_events, get_trip_context
from app.disruption.communication.messages import Delivery, PassengerMessage, build_message, deliver
from app.disruption.contracts import Decision, ResolveRequest, TraceEntry, TripState
from app.disruption.entitlements.service import decide
from app.disruption.entitlements.sources import get_eligible_options, get_policy_rules

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


def resolve_disruption(request: ResolveRequest, *, write_tools: WriteTools | None = None) -> Resolution:
    now = request.now or datetime.now(timezone.utc)
    tools = write_tools if write_tools is not None else MockWriteTools()

    trip = get_trip_context(request.booking_id)
    events = get_operational_events([s["segment_id"] for s in trip["segments"]])
    state = assess_trip(trip, events)

    decision = decide(
        state,
        policy=get_policy_rules(POLICY_SCENARIO),
        options_response=get_eligible_options(trip),
        request=request,
        now=now,
        refetch_options=lambda: get_eligible_options(trip),
    )

    actions = execute_actions(decision, state, tools)
    message = build_message(state, decision, actions)
    delivery = deliver(message, tools)

    trace = [*state.trace, *decision.trace, *actions.trace, *delivery.trace]
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
