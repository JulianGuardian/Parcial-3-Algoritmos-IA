"""Minimal, mock-data-backed entitlements evaluation.

NOTE: deliberately simplified stand-in for the full entitlements layer
(tasks 3.1-3.4: rule evaluation, option filtering, recommendation,
human-approval gate). It is enough to produce a real `Decision` for
`ABC123` so 6.x (answer agent) has genuine data to read through the
facade. Must be replaced/reconciled once tasks 3.1-3.4 are done.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.disruption.contracts import (
    AppliedRule,
    Decision,
    NotApplicableRule,
    RejectedOption,
    TraceEntry,
    TripState,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str) -> dict:
    with (FIXTURES_DIR / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def get_policy_rules() -> dict:
    return _load("get_policy_rules_DELAY.json")


def get_eligible_options(booking_id: str) -> dict:
    if booking_id != "ABC123":
        raise LookupError(f"unknown booking_id: {booking_id}")
    return _load("get_eligible_options_ABC123.json")


def evaluate_entitlements(
    trip: TripState,
    compensation_requested: bool = False,
) -> Decision:
    policy = get_policy_rules()
    options_doc = get_eligible_options(trip.booking_id)

    missed_connection = any(s.missed_connection for s in trip.segments)
    max_delay = max((s.delay_minutes for s in trip.segments), default=0)

    conditions = {
        "R1": max_delay >= 180,
        "R2": False,  # international meal voucher: not evaluated without route data
        "R3": missed_connection,
        "R4": compensation_requested,
        "R5": trip.has_minor,
    }

    applied: list[AppliedRule] = []
    not_applied: list[NotApplicableRule] = []
    human_reasons: list[str] = []
    for rule in policy["rules"]:
        rid = rule["rule_id"]
        if conditions.get(rid):
            applied.append(AppliedRule(rule_id=rid, entitlement=rule["entitlement"]))
            if rule.get("requires_human_approval"):
                human_reasons.append(f"{rid}_{rule['entitlement']}")
        else:
            not_applied.append(NotApplicableRule(rule_id=rid, reason="condition_not_met"))

    # Option filtering: TTL -> seats -> policy consistency -> confidence.
    rejected: list[RejectedOption] = []
    recommended: dict | None = None
    for opt in options_doc["options"]:
        if opt["type"] != "REBOOK":
            rejected.append(RejectedOption(option_id=opt["option_id"], reason="POLICY_INCONSISTENT"))
            continue
        if opt.get("seats_available", 0) < trip.party_size:
            rejected.append(RejectedOption(option_id=opt["option_id"], reason="INSUFFICIENT_SEATS"))
            continue
        if opt.get("fare_difference", 0) > 0:
            rejected.append(RejectedOption(option_id=opt["option_id"], reason="POLICY_INCONSISTENT"))
            continue
        if recommended is None:
            recommended = opt
        else:
            rejected.append(RejectedOption(option_id=opt["option_id"], reason="REQUIRES_AGENT_REVIEW"))

    requires_human = bool(human_reasons) or trip.assessment_status == "CONFLICTING"

    trace = [
        TraceEntry(
            step="entitlements",
            detail={"applied_rules": [a.rule_id for a in applied]},
        )
    ]

    return Decision(
        booking_id=trip.booking_id,
        applied_rules=applied,
        not_applied_rules=not_applied,
        policy_ref=policy["version"],
        recommended_option=recommended,
        rejected_options=rejected,
        requires_human=requires_human,
        human_reasons=human_reasons,
        auto_deliverable=not requires_human,
        trace=trace,
    )
