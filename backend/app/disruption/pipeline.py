"""Orchestrator wiring intake -> assessment -> entitlements -> answer agent.

NOTE: this is a minimal stand-in for the full `resolve_disruption` pipeline
(task 5.4: chaining through the controlled actions and communication
layers once tasks 5.1-5.3 exist). Assessment (2.x) and entitlements (3.x)
are now the real implementations from `app.disruption.assessment` and
`app.disruption.entitlements`. What is still missing is the actions layer
(write adapters, idempotency, retries) and the template-based message
builder; this module calls the answer agent directly instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.config import Settings
from app.disruption.agents.answer_agent import answer_question
from app.disruption.assessment.service import assess_trip
from app.disruption.assessment.sources import get_operational_events, get_trip_context
from app.disruption.contracts import Decision, ResolveRequest, TraceEntry, TripState
from app.disruption.entitlements.service import decide
from app.disruption.entitlements.sources import get_eligible_options, get_policy_rules
from app.disruption.intake.service import classify_question

# Assumption: the exam fixtures cover a single policy scenario; a real
# deployment would derive the scenario from the trip/disruption type.
_POLICY_SCENARIO = "DELAY"


@dataclass
class ResolutionResult:
    trip: TripState
    decision: Decision
    message: str | None
    trace: list[TraceEntry]


def resolve_disruption(request: ResolveRequest, settings: Settings) -> ResolutionResult:
    trace: list[TraceEntry] = []
    now = request.now or datetime.now(timezone.utc)

    intake = classify_question(
        request.question,
        classifier_backend=settings.intent_classifier,
        adk_model=settings.intent_model,
        adk_api_key=settings.intent_model_api_key,
    )
    compensation_from_question = False
    if intake is not None:
        trace.append(intake.trace)
        compensation_from_question = intake.intent_result.compensation_requested

    trip_context = get_trip_context(request.booking_id)
    events = get_operational_events([s["segment_id"] for s in trip_context["segments"]])
    trip = assess_trip(trip_context, events)
    trace.extend(trip.trace)

    policy = get_policy_rules(_POLICY_SCENARIO)
    options_response = get_eligible_options(trip_context)
    effective_request = ResolveRequest(
        booking_id=request.booking_id,
        now=now,
        question=request.question,
        compensation_requested=request.compensation_requested or compensation_from_question,
        wants_same_day=request.wants_same_day,
    )
    decision = decide(
        trip,
        policy=policy,
        options_response=options_response,
        request=effective_request,
        now=now,
        refetch_options=lambda: get_eligible_options(trip_context),
    )
    trace.extend(decision.trace)

    message: str | None = None
    if request.question:
        answer = answer_question(
            request.question,
            trip,
            decision,
            model=settings.intent_model,
            api_key=settings.intent_model_api_key,
        )
        message = answer.message
        trace.append(answer.trace)

    return ResolutionResult(trip=trip, decision=decision, message=message, trace=trace)
