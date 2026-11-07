"""Safe read-only facade for the answer agent (task 6.1, design D13).

These functions are built over the `TripState`/`Decision` the deterministic
pipeline already computed for the *current* request - never over the raw
exam tools. None of them accepts a `booking_id` or any passenger
identifier: each is closed over the request being resolved, so the agent
cannot read another booking. There are no write tools here.
"""

from __future__ import annotations

from app.disruption.contracts import Decision, TripState


class DisruptionToolsFacade:
    """Bound to one `TripState`/`Decision` pair for a single request."""

    def __init__(self, trip: TripState, decision: Decision):
        self._trip = trip
        self._decision = decision

    def get_trip_summary(self) -> dict:
        """Reconciled per-segment status and the missed-connection flag.

        No personal data, and no discarded or degraded events - those were
        already excluded when `TripState` was assessed.
        """
        return {
            "booking_id": self._trip.booking_id,
            "segments": [
                {
                    "segment_id": s.segment_id,
                    "flight_number": s.flight_number,
                    "status": s.status.value,
                    "delay_minutes": s.delay_minutes,
                    "estimated_arrival": s.estimated_arrival.isoformat() if s.estimated_arrival else None,
                    "missed_connection": s.missed_connection,
                }
                for s in self._trip.segments
            ],
        }

    def get_entitlements(self) -> dict:
        """Applied rules, the recommended option, and the human-approval
        gate. Rejected options are reduced to a count, with no details."""
        option = self._decision.recommended_option
        recommended = None
        if option is not None:
            recommended = {
                "option_id": option.option_id,
                "flight_number": option.flight_number,
                "date": option.date,
                "departure": option.departure,
            }
        return {
            "applied_rules": [r.rule_id for r in self._decision.applied_rules],
            "recommended_option": recommended,
            "requires_human": self._decision.requires_human,
            "human_reasons": list(self._decision.human_reasons),
            "rejected_option_count": len(self._decision.rejected_options),
            "policy_ref": self._decision.policy_ref,
        }

    def get_policy_rule(self, rule_id: str) -> dict | None:
        """The text of one rule from the current policy version only."""
        for rule in self._decision.applied_rules:
            if rule.rule_id == rule_id:
                return {
                    "rule_id": rule.rule_id,
                    "entitlement": rule.entitlement,
                    "policy_ref": self._decision.policy_ref,
                }
        return None
