"""Shared contract between the agent tools and the agent workflow.

Change `build-disruption-agent`, design D2, D4 and D5. The tools, the
guardrails and the response builder (`agents/disruption_tools.py`,
`agents/guardrails.py` and `agents/response.py`) produce these shapes; the
workflow, the API and the evaluations consume them.

Session state is plain JSON (ADK keeps it in the session), so every value
stored under a `STATE_*` key is a dict or list produced with `model_dump()`.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Session-state keys
# --------------------------------------------------------------------------- #
STATE_BOOKING_ID = "booking_id"  # set by the API when the conversation starts
STATE_INTAKE = "intake"  # IntentResult dump written by intent_classifier (output_key)
STATE_CONFIRMED_OPTION = "confirmed_option_id"  # set by the API from confirm_option_id only
STATE_NOW = "now"  # optional ISO-8601 evaluation time (pins TTL/freshness)
STATE_TOOL_LOG = "tool_log"  # list[ToolLogEntry dump], one entry per tool call this turn
STATE_HUMAN_CASE = "human_case"  # EscalationResult dump once a case exists
STATE_REBOOKING = "rebooking"  # RebookingResult dump once a rebooking was attempted

# --------------------------------------------------------------------------- #
# Tool names (the only tools any agent may see)
# --------------------------------------------------------------------------- #
GET_TRIP_STATUS = "get_trip_status"
GET_ENTITLEMENTS = "get_entitlements"
GET_POLICY_RULE = "get_policy_rule"
REQUEST_REBOOKING = "request_rebooking"
ESCALATE_TO_HUMAN = "escalate_to_human"

READ_TOOLS = frozenset({GET_TRIP_STATUS, GET_ENTITLEMENTS, GET_POLICY_RULE})
WRITE_TOOLS = frozenset({REQUEST_REBOOKING, ESCALATE_TO_HUMAN})


class EscalationReason(StrEnum):
    POLICY_REQUIRES_HUMAN = "POLICY_REQUIRES_HUMAN"
    PASSENGER_REQUEST = "PASSENGER_REQUEST"
    UNRESOLVED_DATA = "UNRESOLVED_DATA"
    REBOOKING_INDETERMINATE = "REBOOKING_INDETERMINATE"


class BlockReason(StrEnum):
    NOT_CONFIRMED = "NOT_CONFIRMED"
    OPTION_NOT_VALID = "OPTION_NOT_VALID"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NO_BOOKING = "NO_BOOKING"


class NextStep(StrEnum):
    CONFIRM_OPTION = "CONFIRM_OPTION"
    AGENT_WILL_CONTACT = "AGENT_WILL_CONTACT"
    REBOOKING_PENDING = "REBOOKING_PENDING"
    VERIFYING = "VERIFYING"
    NO_ACTION_NEEDED = "NO_ACTION_NEEDED"


# --------------------------------------------------------------------------- #
# Tool results (whitelisted fields only; no free text from the sources)
# --------------------------------------------------------------------------- #
class SegmentView(BaseModel):
    segment_id: str
    flight_number: str
    origin: str
    destination: str
    status: str
    delay_minutes: int
    scheduled_departure: str | None = None
    estimated_departure: str | None = None
    estimated_arrival: str | None = None
    missed_connection: bool = False


class TripStatusResult(BaseModel):
    assessment_status: str
    relevant: bool
    party_size: int
    has_minor: bool
    lead_first_name: str | None = None
    segments: list[SegmentView]


class RuleView(BaseModel):
    rule_id: str
    entitlement: str
    policy_ref: str
    requires_human_approval: bool


class OptionView(BaseModel):
    option_id: str
    type: str
    flight_number: str | None = None
    origin: str | None = None
    destination: str | None = None
    date: str | None = None
    departure: str | None = None
    fare_difference: int | None = None
    currency: str | None = None


class EntitlementsResult(BaseModel):
    assessment_status: str
    policy_ref: str | None
    applied_rules: list[RuleView]
    valid_options: list[OptionView]
    recommended_option_id: str | None
    rejected_option_count: int
    requires_human: bool
    human_reasons: list[str]


class PolicyRuleResult(BaseModel):
    rule_id: str
    entitlement: str
    requires_human_approval: bool
    policy_ref: str


class RebookingResult(BaseModel):
    status: str  # PENDING | ALREADY_EXISTS | INDETERMINATE | BLOCKED
    option_id: str
    request_id: str | None = None
    expires_at: str | None = None
    attempts: int = 0
    blocked_reason: BlockReason | None = None


class EscalationResult(BaseModel):
    case_id: str
    queue: str
    sla_minutes: int
    reasons: list[str]
    enforced_by_code: bool = False


class ToolLogEntry(BaseModel):
    tool: str
    args: dict = Field(default_factory=dict)
    outcome: str  # "ok" | "blocked:<reason>" | "error:<code>" | "enforced_by_code"
    latency_ms: float = 0.0


# --------------------------------------------------------------------------- #
# Structured response of one turn (design D5)
# --------------------------------------------------------------------------- #
class EntitlementOut(BaseModel):
    rule_id: str
    entitlement: str
    policy_ref: str


class AgentResponse(BaseModel):
    what_happened: list[str]
    entitlements: list[EntitlementOut]
    options: list[OptionView]
    next_step: NextStep
    policy_refs: list[str]
    human_required: bool
    human_case_id: str | None = None
    rebooking_status: str | None = None
    reply: str
    reply_fallback: str | None = None  # validator reason when the template replaced the draft
    degraded: bool = False
    trajectory: list[str] = Field(default_factory=list)
