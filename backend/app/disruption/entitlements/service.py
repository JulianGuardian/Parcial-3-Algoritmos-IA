"""Entitlements layer entry point: `TripState` + tools output -> `Decision`.

Human approval gate (spec): `requires_human` is true when an applied rule has
`requires_human_approval`, when the assessment is CONFLICTING or UNVERIFIED,
or when data needed by an applied entitlement is missing. The gate blocks
execution of the recommendation, not the explanation.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.disruption.contracts import (
    AssessmentStatus,
    Decision,
    MissingField,
    ResolveRequest,
    TraceEntry,
    TripState,
)
from app.disruption.entitlements.options import REBOOK_ENTITLEMENTS, filter_options, options_expired, recommend
from app.disruption.entitlements.rules import build_context, evaluate_rules

# Fields each entitlement needs in order to be executed safely (design D8).
# A field that is missing but absent from this table is listed, not blocking.
REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "REBOOK_NO_FEE": frozenset(),
    "REBOOK_WITH_FEE": frozenset({"fare_conditions.change_penalty_amount"}),
    "MEAL_VOUCHER": frozenset(),
    "CASH_COMPENSATION": frozenset(),
    "PRIORITY_HANDLING": frozenset(),
}


def decide(
    state: TripState,
    *,
    policy: dict[str, Any],
    options_response: dict[str, Any],
    request: ResolveRequest,
    now: datetime,
    refetch_options: Callable[[], dict[str, Any]] | None = None,
) -> Decision:
    decision = Decision(booking_id=state.booking_id)

    if state.assessment_status in (AssessmentStatus.CONFLICTING, AssessmentStatus.UNVERIFIED):
        reason = f"ASSESSMENT_{state.assessment_status.value}"
        decision.requires_human = True
        decision.human_reasons.append(reason)
        decision.missing_fields = [MissingField(name, False) for name in state.missing_fields]
        decision.trace.append(
            TraceEntry("entitlements", f"{reason}: no rules evaluated, no recommendation", {})
        )
        return decision

    if not state.relevant:
        decision.missing_fields = [MissingField(name, False) for name in state.missing_fields]
        decision.trace.append(
            TraceEntry("entitlements", "informational change only: no entitlement evaluated", {})
        )
        return decision

    context = build_context(state, compensation_requested=request.compensation_requested)
    evaluation = evaluate_rules(policy, context)
    decision.policy_ref = evaluation.policy_ref
    decision.applied_rules = evaluation.applied
    decision.not_applied_rules = evaluation.not_applied
    decision.trace.append(
        TraceEntry(
            "rules",
            f"policy {evaluation.policy_ref}: applied {[r.rule_id for r in evaluation.applied]}",
            {
                "applied": {r.rule_id: r.reason for r in evaluation.applied},
                "not_applied": {r.rule_id: r.reason for r in evaluation.not_applied},
            },
        )
    )

    entitlements = {r.entitlement for r in evaluation.applied}
    if entitlements & REBOOK_ENTITLEMENTS:
        _select_option(decision, state, entitlements, options_response, now, refetch_options)

    _apply_human_gate(decision, state, evaluation.missing_inputs, entitlements)
    decision.auto_deliverable = decision.recommended_option is not None and not decision.requires_human
    return decision


def _select_option(
    decision: Decision,
    state: TripState,
    entitlements: set[str],
    options_response: dict[str, Any],
    now: datetime,
    refetch_options: Callable[[], dict[str, Any]] | None,
) -> None:
    if options_expired(options_response, now) and refetch_options is not None:
        decision.trace.append(TraceEntry("options", "options past TTL: re-fetched once", {}))
        options_response = refetch_options()

    result = filter_options(
        options_response,
        now=now,
        party_size=state.party_size,
        entitlements=entitlements,
        policy_ref=decision.policy_ref or "",
        fare=state.fare_conditions,
    )
    decision.rejected_options = result.rejected
    decision.recommended_option = recommend(result.valid)
    decision.trace.append(
        TraceEntry(
            "options",
            f"recommended {decision.recommended_option.option_id if decision.recommended_option else None}",
            {"rejected": {r.option_id: [x.value for x in r.reasons] for r in result.rejected}},
        )
    )


def _apply_human_gate(
    decision: Decision,
    state: TripState,
    unknown_inputs: list[str],
    entitlements: set[str],
) -> None:
    needed = frozenset().union(*(REQUIRED_FIELDS.get(e, frozenset()) for e in entitlements))
    missing = [MissingField(name, name in needed) for name in state.missing_fields]
    missing += [MissingField(name, True) for name in unknown_inputs]
    decision.missing_fields = missing

    for rule in decision.applied_rules:
        if rule.requires_human_approval:
            decision.human_reasons.append(f"{rule.rule_id}_{rule.entitlement}")
    if any(m.decision_relevant for m in missing):
        decision.human_reasons.append("MISSING_DECISION_DATA")
    decision.requires_human = bool(decision.human_reasons)
    decision.trace.append(
        TraceEntry(
            "human_gate",
            f"requires_human={decision.requires_human}",
            {"reasons": decision.human_reasons, "missing": {m.name: m.decision_relevant for m in missing}},
        )
    )
