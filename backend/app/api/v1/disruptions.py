"""HTTP adapter for disruption resolution (design D10).

`POST /api/v1/disruptions/{booking_id}/resolve` runs the deterministic
pipeline and returns the traceable decision. It is a POST because it can
trigger writes (a human case, a notification). Escalation to a human is a
valid outcome, so it is a 200. The response models leave personal data out:
passengers appear only as counts, never with contact details or documents.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_request_id
from app.disruption.contracts import BookingNotFound, ResolveRequest, ToolUnavailable
from app.disruption.pipeline import Resolution, resolve_disruption

router = APIRouter(prefix="/disruptions", tags=["disruptions"])


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #
class ResolveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    now: datetime | None = Field(
        default=None,
        description="Evaluation time (ISO 8601). Pins TTL and freshness checks; defaults to the current time.",
    )
    question: str | None = Field(default=None, max_length=500, description="Passenger's free-text question.")
    compensation_requested: bool = False


# --------------------------------------------------------------------------- #
# Response (mirrors the domain dataclasses, without personal data)
# --------------------------------------------------------------------------- #
class _FromDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SegmentOut(_FromDomain):
    segment_id: str
    flight_number: str
    origin: str
    destination: str
    status: str
    delay_minutes: int
    scheduled_departure: datetime | None
    scheduled_arrival: datetime | None
    estimated_departure: datetime | None
    estimated_arrival: datetime | None
    missed_connection: bool


class DiscardedEventOut(_FromDomain):
    event_id: str
    reason: str
    detail: str


class AssessmentOut(BaseModel):
    status: str
    relevant: bool
    relevance_reasons: list[str]
    informational_changes: list[str]
    party_size: int
    has_minor: bool
    segments: list[SegmentOut]
    discarded_events: list[DiscardedEventOut]


class RuleOut(_FromDomain):
    rule_id: str
    entitlement: str
    applied: bool
    reason: str
    requires_human_approval: bool


class OptionOut(_FromDomain):
    option_id: str
    type: str
    policy_ref: str | None
    flight_number: str | None
    origin: str | None
    destination: str | None
    date: str | None
    departure: str | None
    fare_difference: int | None
    currency: str | None


class RejectedOptionOut(_FromDomain):
    option_id: str
    reasons: list[str]
    detail: str


class MissingFieldOut(_FromDomain):
    name: str
    decision_relevant: bool


class DecisionOut(_FromDomain):
    policy_ref: str | None
    applied_rules: list[RuleOut]
    not_applied_rules: list[RuleOut]
    recommended_option: OptionOut | None
    rejected_options: list[RejectedOptionOut]
    missing_fields: list[MissingFieldOut]
    requires_human: bool
    human_reasons: list[str]
    auto_deliverable: bool


class RebookingOut(_FromDomain):
    status: str
    idempotency_key: str | None
    request_id: str | None
    expires_at: str | None
    attempts: int


class HumanCaseOut(_FromDomain):
    case_id: str
    queue: str
    sla_minutes: int
    reasons: list[str]


class ActionsOut(_FromDomain):
    rebooking: RebookingOut
    human_case: HumanCaseOut | None


class NotificationOut(BaseModel):
    status: str
    text: str
    policy_ref: str | None
    agent_follow_up: bool
    notification_id: str | None
    channel: str | None
    error: str | None


class TraceEntryOut(_FromDomain):
    step: str
    message: str
    data: dict[str, Any]


class ResolutionOut(BaseModel):
    booking_id: str
    evaluated_at: datetime
    request_id: str | None
    assessment: AssessmentOut
    decision: DecisionOut
    actions: ActionsOut
    notification: NotificationOut
    trace: list[TraceEntryOut]


class ErrorOut(BaseModel):
    error: str
    detail: str
    request_id: str | None


# --------------------------------------------------------------------------- #
# Route
# --------------------------------------------------------------------------- #
@router.post(
    "/{booking_id}/resolve",
    response_model=ResolutionOut,
    responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}},
)
def resolve(booking_id: str, body: ResolveBody | None = Body(default=None)) -> ResolutionOut | JSONResponse:
    body = body or ResolveBody()
    request = ResolveRequest(
        booking_id=booking_id,
        now=body.now,
        question=body.question,
        compensation_requested=body.compensation_requested,
    )
    try:
        resolution = resolve_disruption(request)
    except BookingNotFound:
        return _error(404, "BOOKING_NOT_FOUND", "No booking matches this id.")
    except ToolUnavailable:
        return _error(503, "UPSTREAM_UNAVAILABLE", "A required data source is unavailable. Try again later.")
    return _to_response(resolution)


def _error(status: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorOut(error=error, detail=detail, request_id=get_request_id()).model_dump(),
    )


def _to_response(resolution: Resolution) -> ResolutionOut:
    state = resolution.state
    return ResolutionOut(
        booking_id=state.booking_id,
        evaluated_at=resolution.evaluated_at,
        request_id=get_request_id(),
        assessment=AssessmentOut(
            status=state.assessment_status,
            relevant=state.relevant,
            relevance_reasons=state.relevance_reasons,
            informational_changes=state.informational_changes,
            party_size=state.party_size,
            has_minor=state.has_minor,
            segments=[SegmentOut.model_validate(s) for s in state.segments],
            discarded_events=[DiscardedEventOut.model_validate(e) for e in state.discarded_events],
        ),
        decision=DecisionOut.model_validate(resolution.decision),
        actions=ActionsOut.model_validate(resolution.actions),
        notification=NotificationOut(
            status=resolution.delivery.status,
            text=resolution.message.text,
            policy_ref=resolution.message.policy_ref,
            agent_follow_up=resolution.message.agent_follow_up,
            notification_id=resolution.delivery.notification_id,
            channel=resolution.delivery.channel,
            error=resolution.delivery.error,
        ),
        trace=[TraceEntryOut.model_validate(t) for t in resolution.trace],
    )
