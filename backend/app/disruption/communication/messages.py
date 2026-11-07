"""Passenger message builder and delivery (spec `passenger-communication`).

Messages are filled from fixed templates with validated facts only:
- what happened to the passenger's segments and its consequence;
- the recommended option and the entitlement behind it;
- whether an agent will follow up;
- the `policy_ref`.

Internal source names, discarded events, confidence levels, rejected options
and personal data other than first names never reach the text. A message
without a `policy_ref` is never sent; a 422 from the tool blocks delivery and
is not retried.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.disruption.actions.service import ActionResult, RebookingStatus, WriteTools
from app.disruption.contracts import (
    AssessmentStatus,
    Decision,
    SegmentState,
    SegmentStatus,
    TraceEntry,
    TripState,
)

NO_FEE_ENTITLEMENTS = {"REBOOK_NO_FEE"}


class DeliveryStatus(StrEnum):
    SENT = "SENT"
    BLOCKED = "BLOCKED"
    NOT_SENT = "NOT_SENT"


@dataclass(frozen=True)
class PassengerMessage:
    text: str
    policy_ref: str | None
    agent_follow_up: bool


@dataclass
class Delivery:
    status: DeliveryStatus
    notification_id: str | None = None
    channel: str | None = None
    error: str | None = None
    trace: list[TraceEntry] = field(default_factory=list)


def build_message(state: TripState, decision: Decision, actions: ActionResult) -> PassengerMessage:
    lines = [_greeting(state)]

    if state.assessment_status in (AssessmentStatus.CONFLICTING, AssessmentStatus.UNVERIFIED):
        lines.append("We are still confirming the latest status of your trip.")
    else:
        lines.extend(describe_what_happened(state))

    entitlements = {r.entitlement for r in decision.applied_rules}
    option = decision.recommended_option
    if option is not None and option.type == "REBOOK":
        cost = " at no extra cost" if entitlements & NO_FEE_ENTITLEMENTS else ""
        lines.append(
            f"We can offer you flight {option.flight_number} from {option.origin} to "
            f"{option.destination} on {option.date} at {option.departure}{cost}."
        )

    if "CASH_COMPENSATION" in entitlements:
        lines.append("An agent will review your compensation request.")

    follow_up = actions.escalated
    if follow_up:
        if option is not None:
            lines.append("An agent will contact you to confirm this option before any change is made.")
        else:
            lines.append("An agent will contact you with your options.")
    elif actions.rebooking.status in (RebookingStatus.PENDING, RebookingStatus.ALREADY_EXISTS):
        lines.append("We have requested this change; you will receive a confirmation once it is completed.")
    elif option is not None and option.type == "REBOOK":
        lines.append("Please confirm this option if you want us to request the change.")

    if decision.policy_ref:
        lines.append(f"Policy reference: {decision.policy_ref}.")

    return PassengerMessage(text=" ".join(lines), policy_ref=decision.policy_ref, agent_follow_up=follow_up)


def deliver(message: PassengerMessage, tools: WriteTools) -> Delivery:
    if not message.policy_ref:
        return Delivery(
            DeliveryStatus.NOT_SENT,
            error="missing policy_ref",
            trace=[TraceEntry("notification", "not sent: no policy_ref to back the message", {})],
        )

    response = tools.notify_passenger(message_payload(message))
    if response.ok:
        return Delivery(
            DeliveryStatus.SENT,
            notification_id=response.body.get("notification_id"),
            channel=response.body.get("channel"),
            trace=[TraceEntry("notification", f"queued ({response.status_code})", {})],
        )

    error = response.body.get("error", f"HTTP {response.status_code}")
    detail = response.body.get("detail")
    return Delivery(
        DeliveryStatus.BLOCKED,
        error=f"{error}: {detail}" if detail else error,
        trace=[
            TraceEntry(
                "notification",
                f"blocked by notify_passenger ({response.status_code}); not retried",
                {"error": error, "detail": detail},
            )
        ],
    )


def _greeting(state: TripState) -> str:
    adults = [p for p in state.passengers if p.type == "ADULT"]
    lead = adults[0] if adults else (state.passengers[0] if state.passengers else None)
    return f"Hello {lead.first_name}." if lead and lead.first_name else "Hello."


def describe_what_happened(state: TripState) -> list[str]:
    lines: list[str] = []
    for segment in state.segments:
        if segment.status is SegmentStatus.DELAYED and segment.delay_minutes:
            lines.append(_delay_line(segment))
        elif segment.status is SegmentStatus.CANCELLED:
            lines.append(f"Your flight {segment.flight_number} from {segment.origin} to {segment.destination} was cancelled.")
        if segment.missed_connection:
            lines.append(
                f"Because of this you will miss your connection {segment.flight_number} "
                f"from {segment.origin} to {segment.destination}."
            )
    if not lines:
        lines.append("There are no changes to your trip that require action.")
    return lines


def _delay_line(segment: SegmentState) -> str:
    new_time = f" (new departure {segment.estimated_departure:%H:%M})" if segment.estimated_departure else ""
    return (
        f"Your flight {segment.flight_number} from {segment.origin} to {segment.destination} "
        f"is delayed by {segment.delay_minutes} minutes{new_time}."
    )


def message_payload(message: PassengerMessage) -> dict[str, Any]:
    return {"text": message.text, "policy_ref": message.policy_ref}
