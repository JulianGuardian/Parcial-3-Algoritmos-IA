"""Faithfulness check for an agent response (task 5.1, spec `agent-evaluation`).

A code check rather than an LLM-as-judge, so the result is deterministic.
It holds when:
- every entitlement in the response maps to a rule the `get_entitlements`
  tool reported as applied, with the same `policy_ref`;
- every `policy_ref` in the response was returned by that tool;
- every flight number mentioned in the reply belongs to `options`, or is
  one of the passenger's own segments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.disruption.agents.contracts import AgentResponse, EntitlementsResult, TripStatusResult

_FLIGHT = re.compile(r"\b[A-Z]{2}\d{3,4}\b")


@dataclass
class FaithfulnessResult:
    ok: bool
    problems: list[str] = field(default_factory=list)


def check_faithfulness(
    response: AgentResponse,
    entitlements: EntitlementsResult,
    trip_status: TripStatusResult | None = None,
) -> FaithfulnessResult:
    problems: list[str] = []
    backed = {(r.rule_id, r.entitlement, r.policy_ref) for r in entitlements.applied_rules}
    returned_refs = {r.policy_ref for r in entitlements.applied_rules}
    if entitlements.policy_ref:
        returned_refs.add(entitlements.policy_ref)

    for item in response.entitlements:
        if (item.rule_id, item.entitlement, item.policy_ref) not in backed:
            problems.append(f"unbacked entitlement {item.entitlement} ({item.rule_id}, {item.policy_ref})")
    for ref in response.policy_refs:
        if ref not in returned_refs:
            problems.append(f"policy_ref {ref} not returned by any tool")

    allowed_flights = {o.flight_number for o in response.options if o.flight_number}
    if trip_status is not None:
        allowed_flights |= {s.flight_number for s in trip_status.segments}
    for flight in sorted(set(_FLIGHT.findall(response.reply)) - allowed_flights):
        problems.append(f"reply mentions flight {flight} outside options")

    return FaithfulnessResult(ok=not problems, problems=problems)
