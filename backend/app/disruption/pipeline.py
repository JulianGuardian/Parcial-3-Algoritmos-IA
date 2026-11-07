"""Minimal orchestrator wiring intake -> assessment -> entitlements -> answer agent.

NOTE: this is a deliberately minimal stand-in for the full `resolve_disruption`
pipeline (tasks 5.1-5.5: write actions with idempotency/retry, the
template-based message builder, the real HTTP route semantics). It exists
so the Persona 2 work (intake 4.x, answer agent 6.x) has a real end-to-end
path to run through for the Docker smoke test (task 5.6), and so Docker
startup with `google-adk` installed can be verified against a live
request. It must be replaced/reconciled once tasks 5.1-5.5 are implemented
for real (write adapters, idempotent actions, 409/503/422 handling).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.disruption.agents.answer_agent import answer_question
from app.disruption.assessment.mock import assess_trip
from app.disruption.contracts import Decision, TraceEntry, TripState
from app.disruption.entitlements.mock import evaluate_entitlements
from app.disruption.intake.service import classify_question


@dataclass
class ResolutionResult:
    trip: TripState
    decision: Decision
    message: str | None
    trace: list[TraceEntry]


def resolve_disruption(
    booking_id: str,
    settings: Settings,
    question: str | None = None,
    compensation_requested: bool = False,
) -> ResolutionResult:
    trace: list[TraceEntry] = []

    intake = classify_question(
        question,
        classifier_backend=settings.intent_classifier,
        adk_model=settings.intent_model,
        adk_api_key=settings.intent_model_api_key,
    )
    compensation_from_question = False
    if intake is not None:
        trace.append(intake.trace)
        compensation_from_question = intake.intent_result.compensation_requested

    trip = assess_trip(booking_id)
    trace.extend(trip.trace)

    decision = evaluate_entitlements(
        trip,
        compensation_requested=compensation_requested or compensation_from_question,
    )
    trace.extend(decision.trace)

    message: str | None = None
    if question:
        answer = answer_question(
            question,
            trip,
            decision,
            model=settings.intent_model,
            api_key=settings.intent_model_api_key,
        )
        message = answer.message
        trace.append(answer.trace)

    return ResolutionResult(trip=trip, decision=decision, message=message, trace=trace)
