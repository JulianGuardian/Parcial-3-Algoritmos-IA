"""Shared data contracts of the disruption domain (design D2).

The three layers (assessment -> entitlements -> actions/communication) talk to
each other only through these dataclasses. This module is plain Python: no
FastAPI, no I/O.

Personal data never appears here: `assessment` strips `document_id`, surnames
and raw contact details before building a `TripState`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


# --------------------------------------------------------------------------- #
# Errors raised by the (mock) tools. The HTTP layer maps them to 404 / 503.
# --------------------------------------------------------------------------- #
class BookingNotFound(Exception):
    """The booking id is unknown to the trip-context tool."""


class ToolUnavailable(Exception):
    """A required read tool failed or returned nothing usable."""


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class SegmentStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    ON_TIME = "ON_TIME"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


class AssessmentStatus(StrEnum):
    OK = "OK"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"
    NO_RELEVANT_CHANGE = "NO_RELEVANT_CHANGE"


class DiscardReason(StrEnum):
    DEGRADED_SOURCE = "DEGRADED_SOURCE"
    STALE = "STALE"
    SUPERSEDED_BY_HIGHER_PRIORITY = "SUPERSEDED_BY_HIGHER_PRIORITY"
    SUPERSEDED_BY_NEWER_EVENT = "SUPERSEDED_BY_NEWER_EVENT"


class RejectionReason(StrEnum):
    EXPIRED = "EXPIRED"
    INSUFFICIENT_SEATS = "INSUFFICIENT_SEATS"
    POLICY_INCONSISTENT = "POLICY_INCONSISTENT"
    REQUIRES_AGENT_REVIEW = "REQUIRES_AGENT_REVIEW"


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ResolveRequest:
    booking_id: str
    now: datetime | None = None
    question: str | None = None
    compensation_requested: bool = False
    wants_same_day: bool = False


# --------------------------------------------------------------------------- #
# Trace
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TraceEntry:
    """One explainable step of the pipeline."""

    step: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Assessment output
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PassengerView:
    """Passenger data that may travel downstream (no document id, no surname)."""

    passenger_id: str
    first_name: str
    type: str
    age: int | None = None
    masked_email: str | None = None
    masked_phone: str | None = None


@dataclass(frozen=True)
class FareConditions:
    changeable: bool | None = None
    refundable: bool | None = None
    fare_family: str | None = None


@dataclass(frozen=True)
class DiscardedEvent:
    event_id: str
    reason: DiscardReason
    detail: str = ""


@dataclass
class SegmentState:
    segment_id: str
    flight_number: str
    origin: str
    destination: str
    status: SegmentStatus
    delay_minutes: int = 0
    # Airport-local wall-clock times, as given by the sources (design D5).
    scheduled_departure: datetime | None = None
    scheduled_arrival: datetime | None = None
    estimated_departure: datetime | None = None
    estimated_arrival: datetime | None = None
    missed_connection: bool = False


@dataclass
class TripState:
    booking_id: str
    party_size: int
    has_minor: bool
    passengers: list[PassengerView] = field(default_factory=list)
    fare_conditions: FareConditions = field(default_factory=FareConditions)
    segments: list[SegmentState] = field(default_factory=list)
    assessment_status: AssessmentStatus = AssessmentStatus.NO_RELEVANT_CHANGE
    relevant: bool = False
    relevance_reasons: list[str] = field(default_factory=list)
    informational_changes: list[str] = field(default_factory=list)
    discarded_events: list[DiscardedEvent] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Entitlements output
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    entitlement: str
    applied: bool
    reason: str
    requires_human_approval: bool = False


@dataclass(frozen=True)
class Option:
    option_id: str
    type: str
    policy_ref: str | None = None
    confidence: str | None = None
    flight_number: str | None = None
    origin: str | None = None
    destination: str | None = None
    date: str | None = None
    departure: str | None = None
    fare_difference: int | None = None
    currency: str | None = None
    seats_available: int | None = None


@dataclass(frozen=True)
class RejectedOption:
    option_id: str
    reasons: tuple[RejectionReason, ...]
    detail: str = ""

    @property
    def reason(self) -> RejectionReason:
        """Primary reason: the first check (in design D6 order) that failed."""
        return self.reasons[0]


@dataclass(frozen=True)
class MissingField:
    name: str
    decision_relevant: bool


@dataclass
class Decision:
    booking_id: str
    policy_ref: str | None = None
    applied_rules: list[RuleResult] = field(default_factory=list)
    not_applied_rules: list[RuleResult] = field(default_factory=list)
    recommended_option: Option | None = None
    rejected_options: list[RejectedOption] = field(default_factory=list)
    missing_fields: list[MissingField] = field(default_factory=list)
    requires_human: bool = False
    human_reasons: list[str] = field(default_factory=list)
    # True only when the recommendation could be executed without a human.
    auto_deliverable: bool = False
    trace: list[TraceEntry] = field(default_factory=list)
