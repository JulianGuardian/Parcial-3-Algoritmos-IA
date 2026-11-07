"""Shared data contracts for the disruption domain (design D2).

Plain dataclasses with no FastAPI imports, so every layer (assessment,
entitlements, actions, communication, agents) can be built and tested
without HTTP. Personal data (document id, email, phone) must never be
placed on `TripState` or anything derived from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class ResolveRequest:
    """Input to `resolve_disruption`."""

    booking_id: str
    now: datetime | None = None
    question: str | None = None
    compensation_requested: bool = False
    wants_same_day: bool = False


@dataclass
class SegmentState:
    segment_id: str
    flight_number: str
    status: Literal["ON_TIME", "DELAYED", "CANCELLED", "UNVERIFIED"]
    delay_minutes: int
    estimated_arrival: str | None
    missed_connection: bool


@dataclass
class TraceEntry:
    """One step of the decision trace.

    `step` names the pipeline stage (e.g. "assessment", "intent_classifier",
    "answer_agent"). The remaining fields are free-form per step; agent
    steps additionally carry `framework`, `agent`, `model`, `latency_ms`,
    `fallback_used` as documented in design D12/D13.
    """

    step: str
    detail: dict = field(default_factory=dict)


@dataclass
class TripState:
    booking_id: str
    party_size: int
    has_minor: bool
    segments: list[SegmentState]
    assessment_status: Literal["OK", "CONFLICTING", "UNVERIFIED", "NO_RELEVANT_CHANGE"]
    relevant: bool
    discarded_events: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)


@dataclass
class RejectedOption:
    option_id: str
    reason: Literal[
        "EXPIRED",
        "INSUFFICIENT_SEATS",
        "POLICY_INCONSISTENT",
        "REQUIRES_AGENT_REVIEW",
    ]


@dataclass
class AppliedRule:
    rule_id: str
    entitlement: str


@dataclass
class NotApplicableRule:
    rule_id: str
    reason: str


@dataclass
class Decision:
    booking_id: str
    applied_rules: list[AppliedRule]
    not_applied_rules: list[NotApplicableRule]
    policy_ref: str | None
    recommended_option: dict | None
    rejected_options: list[RejectedOption]
    requires_human: bool
    human_reasons: list[str]
    auto_deliverable: bool
    trace: list[TraceEntry] = field(default_factory=list)
