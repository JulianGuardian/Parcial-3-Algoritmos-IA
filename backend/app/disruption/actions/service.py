"""Controlled high-impact actions (spec `controlled-actions`, design D9).

Rules:
- A decision that requires a human never creates a rebooking request; it
  creates exactly one human case carrying every reason and the evidence.
- A rebooking request is created only through `rebook_option`, for an
  option the passenger confirmed (change build-disruption-agent), with an
  idempotency key derived from the decision. `execute_actions` never rebooks.
- 409 reuses the existing request; 503 is retried once with the same key and,
  if still indeterminate, escalated to a human.
- A 201 `PENDING_CONFIRMATION` is reported as pending, never as confirmed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from app.disruption.actions.write_tools import ToolResponse
from app.disruption.contracts import Decision, Option, TraceEntry, TripState

REBOOKING_INDETERMINATE = "REBOOKING_INDETERMINATE"
MAX_REBOOKING_ATTEMPTS = 2  # first call + one retry with the same key


class WriteTools(Protocol):
    def create_rebooking_request(self, option: dict[str, Any], idempotency_key: str) -> ToolResponse: ...

    def create_human_case(self, reason: str, evidence: dict[str, Any]) -> ToolResponse: ...

    def notify_passenger(self, message: dict[str, Any]) -> ToolResponse: ...


class RebookingStatus(StrEnum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    PENDING = "PENDING"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class RebookingOutcome:
    status: RebookingStatus
    idempotency_key: str | None = None
    request_id: str | None = None
    expires_at: str | None = None
    attempts: int = 0


@dataclass(frozen=True)
class HumanCase:
    case_id: str
    queue: str
    sla_minutes: int
    reasons: tuple[str, ...]


@dataclass
class ActionResult:
    rebooking: RebookingOutcome = field(
        default_factory=lambda: RebookingOutcome(RebookingStatus.NOT_ATTEMPTED)
    )
    human_case: HumanCase | None = None
    trace: list[TraceEntry] = field(default_factory=list)

    @property
    def escalated(self) -> bool:
        return self.human_case is not None


def idempotency_key(booking_id: str, option_id: str, policy_ref: str | None) -> str:
    """Same decision -> same key, so retries never create a second request."""
    raw = f"{booking_id}|{option_id}|{policy_ref or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def execute_actions(decision: Decision, state: TripState, tools: WriteTools) -> ActionResult:
    """Deterministic actions for a decision that nobody has confirmed yet.

    A rebooking is never requested here (spec `controlled-actions`,
    "Rebooking only for a confirmed option"); the passenger must confirm an
    option first, through `rebook_option`. Only escalation happens here.
    """
    result = ActionResult()
    reasons = list(dict.fromkeys(decision.human_reasons))

    if decision.requires_human:
        result.trace.append(
            TraceEntry("actions", "human approval required: rebooking not executed", {"reasons": reasons})
        )
    elif decision.auto_deliverable and is_rebook(decision.recommended_option):
        result.trace.append(
            TraceEntry(
                "actions",
                "awaiting passenger confirmation: rebooking not requested",
                {"option": decision.recommended_option.option_id},
            )
        )
    else:
        result.trace.append(TraceEntry("actions", "no high-impact action to execute", {}))

    if reasons:
        result.human_case = open_human_case(reasons, decision, state, tools)
        result.trace.append(
            TraceEntry(
                "human_case",
                f"case {result.human_case.case_id} in {result.human_case.queue}",
                {"reasons": reasons},
            )
        )
    return result


def is_rebook(option: Option | None) -> bool:
    return option is not None and option.type == "REBOOK"


def rebook_option(
    decision: Decision,
    option: Option,
    tools: WriteTools,
    trace: list[TraceEntry] | None = None,
) -> RebookingOutcome:
    """Request one rebooking for an option the passenger confirmed.

    Callers (the guarded agent tool) are responsible for checking the
    confirmation and the option's validity first. This function only
    guarantees the write semantics: same key for the same decision, 409
    reuse, a single 503 retry, and `INDETERMINATE` instead of guessing.
    """
    trace = trace if trace is not None else []
    key = idempotency_key(decision.booking_id, option.option_id, decision.policy_ref)
    payload = _option_payload(option)

    for attempt in range(1, MAX_REBOOKING_ATTEMPTS + 1):
        response = tools.create_rebooking_request(payload, idempotency_key=key)
        trace.append(
            TraceEntry(
                "rebooking",
                f"attempt {attempt}: HTTP {response.status_code}",
                {"option": option.option_id, "idempotency_key": key},
            )
        )
        if response.status_code == 201:
            return RebookingOutcome(
                RebookingStatus.PENDING,
                idempotency_key=key,
                request_id=response.body.get("request_id"),
                expires_at=response.body.get("expires_at"),
                attempts=attempt,
            )
        if response.status_code == 409:
            return RebookingOutcome(
                RebookingStatus.ALREADY_EXISTS,
                idempotency_key=key,
                request_id=response.body.get("request_id"),
                attempts=attempt,
            )
        if response.status_code != 503:
            break  # unexpected answer: do not guess, escalate below

    return RebookingOutcome(RebookingStatus.INDETERMINATE, idempotency_key=key, attempts=attempt)


def open_human_case(
    reasons: list[str],
    decision: Decision,
    state: TripState,
    tools: WriteTools,
    rebooking: RebookingOutcome | None = None,
    extra_evidence: dict[str, Any] | None = None,
) -> HumanCase:
    """Open exactly one human case; the evidence is always built here, in code."""
    rebooking = rebooking or RebookingOutcome(RebookingStatus.NOT_ATTEMPTED)
    evidence = {**_evidence(reasons, decision, state, rebooking), **(extra_evidence or {})}
    response = tools.create_human_case(",".join(reasons), evidence)
    body = response.body
    return HumanCase(
        case_id=body["case_id"],
        queue=body["queue"],
        sla_minutes=body["sla_minutes"],
        reasons=tuple(reasons),
    )


def _evidence(
    reasons: list[str],
    decision: Decision,
    state: TripState,
    rebooking: RebookingOutcome,
) -> dict[str, Any]:
    """Everything an agent needs, nothing personal beyond ids and first names."""
    recommended = decision.recommended_option
    return {
        "booking_id": decision.booking_id,
        "passengers": [
            {"passenger_id": p.passenger_id, "first_name": p.first_name, "type": p.type} for p in state.passengers
        ],
        "human_reasons": reasons,
        "policy_ref": decision.policy_ref,
        "assessment_status": state.assessment_status.value,
        "applied_rules": [{"rule_id": r.rule_id, "entitlement": r.entitlement} for r in decision.applied_rules],
        "not_applied_rules": [{"rule_id": r.rule_id, "reason": r.reason} for r in decision.not_applied_rules],
        "recommended_option": _option_payload(recommended) if recommended else None,
        "rejected_options": [
            {"option_id": r.option_id, "reasons": [x.value for x in r.reasons]} for r in decision.rejected_options
        ],
        "discarded_events": [{"event_id": e.event_id, "reason": e.reason.value} for e in state.discarded_events],
        "missing_fields": [{"name": m.name, "decision_relevant": m.decision_relevant} for m in decision.missing_fields],
        "rebooking": {"status": rebooking.status.value, "idempotency_key": rebooking.idempotency_key},
    }


def _option_payload(option: Option) -> dict[str, Any]:
    return {k: v for k, v in vars(option).items() if v is not None}
