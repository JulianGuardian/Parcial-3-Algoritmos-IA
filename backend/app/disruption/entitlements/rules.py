"""Deterministic evaluation of the policy rules (R1..R5).

Conditions are the small strings the policy tool returns, for example
`delay_minutes >= 240 AND international`. They are parsed here, never passed
to `eval`. Only the version the tool returns as current is evaluated; fields
such as `superseded_versions` are never read.

Terms are evaluated left to right and stop at the first one that fails, so a
rule that is already false for a reason never reports an unrelated unknown.
"""

import operator
import re
from dataclasses import dataclass, field
from typing import Any

from app.disruption.contracts import RuleResult, SegmentState, SegmentStatus, ToolUnavailable, TripState

# Assumption: the trip context carries no country, so airports map to one here.
# A segment touching an airport that is not listed makes `international`
# unknown, which is reported as missing data instead of guessed.
AIRPORT_COUNTRY = {
    "SCL": "CL", "LIM": "PE", "MEX": "MX", "BOG": "CO", "MDE": "CO", "UIO": "EC",
    "EZE": "AR", "GRU": "BR", "PTY": "PA", "MAD": "ES", "MIA": "US", "JFK": "US",
    "LAX": "US", "CUN": "MX",
}  # fmt: skip

_TERM = re.compile(r"^(?P<name>[a-z_]+)\s*(?:(?P<op>>=|<=|==|!=|>|<)\s*(?P<value>\S+))?$")
_OPS = {">=": operator.ge, "<=": operator.le, "==": operator.eq, "!=": operator.ne, ">": operator.gt, "<": operator.lt}
_NEGATED = {">=": "<", "<=": ">", "==": "!=", "!=": "==", ">": "<=", "<": ">="}


@dataclass(frozen=True)
class RuleContext:
    """Facts the rule conditions may refer to."""

    delay_minutes: int
    missed_connection: bool
    group_includes_minor: bool
    compensation_requested: bool
    international: bool | None  # None = unknown airport country
    unknown_airports: tuple[str, ...] = ()

    def lookup(self, name: str) -> Any:
        if name not in _VARIABLES:
            raise ToolUnavailable(f"policy condition uses unknown variable {name!r}")
        return getattr(self, name)


_VARIABLES = frozenset(
    {"delay_minutes", "missed_connection", "group_includes_minor", "compensation_requested", "international"}
)


@dataclass
class RuleEvaluation:
    policy_ref: str
    applied: list[RuleResult] = field(default_factory=list)
    not_applied: list[RuleResult] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)


def _is_international(segment: SegmentState) -> tuple[bool | None, tuple[str, ...]]:
    origin = AIRPORT_COUNTRY.get(segment.origin)
    destination = AIRPORT_COUNTRY.get(segment.destination)
    unknown = tuple(a for a, c in ((segment.origin, origin), (segment.destination, destination)) if c is None)
    if unknown:
        return None, unknown
    return origin != destination, ()


def build_context(state: TripState, *, compensation_requested: bool) -> RuleContext:
    """Derive the rule inputs from the verified trip.

    `delay_minutes` and `international` describe the most delayed verified
    segment, which is the one a delay entitlement is about.
    """
    delayed = [s for s in state.segments if s.status is SegmentStatus.DELAYED]
    worst = max(delayed, key=lambda s: s.delay_minutes, default=None)
    international, unknown = _is_international(worst) if worst else (False, ())
    return RuleContext(
        delay_minutes=worst.delay_minutes if worst else 0,
        missed_connection=any(s.missed_connection for s in state.segments),
        group_includes_minor=state.has_minor,
        compensation_requested=compensation_requested,
        international=international,
        unknown_airports=unknown,
    )


def _literal(text: str) -> Any:
    lowered = text.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    try:
        return int(text)
    except ValueError as error:
        raise ToolUnavailable(f"policy condition has an unreadable value {text!r}") from error


def _evaluate_term(term: str, context: RuleContext) -> tuple[bool | None, str]:
    """Return (outcome, reason). Outcome None means an input is unknown."""
    match = _TERM.match(term.strip())
    if match is None:
        raise ToolUnavailable(f"unreadable policy condition term {term!r}")
    name, op, raw = match["name"], match["op"], match["value"]
    value = context.lookup(name)
    if value is None:
        return None, f"{name} is unknown"

    if op is None:  # bare flag, e.g. `international`
        return bool(value), (f"{name} is true" if value else f"{name} is false")

    expected = _literal(raw)
    outcome = _OPS[op](value, expected)
    if outcome:
        return True, f"{name} {op} {raw} ({name}={_show(value)})"
    if isinstance(value, bool):
        return False, f"{name} is {_show(value)}, expected {_show(expected)}"
    return False, f"{_show(value)} {_NEGATED[op]} {_show(expected)}"


def _show(value: Any) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def evaluate_condition(condition: str, context: RuleContext) -> tuple[bool, str, bool]:
    """Evaluate `a AND b ...`; returns (applies, reason, input_unknown)."""
    reasons: list[str] = []
    for term in condition.split(" AND "):
        outcome, reason = _evaluate_term(term, context)
        if outcome is None:
            return False, reason, True
        if not outcome:
            return False, reason, False
        reasons.append(reason)
    return True, "; ".join(reasons), False


def evaluate_rules(policy: dict[str, Any], context: RuleContext) -> RuleEvaluation:
    """Evaluate every rule of the current policy version."""
    try:
        version, rules = policy["version"], policy["rules"]
    except KeyError as error:
        raise ToolUnavailable("policy response is missing version or rules") from error

    evaluation = RuleEvaluation(policy_ref=version)
    for rule in rules:
        applies, reason, unknown = evaluate_condition(rule["condition"], context)
        result = RuleResult(
            rule_id=rule["rule_id"],
            entitlement=rule["entitlement"],
            applied=applies,
            reason=reason,
            requires_human_approval=bool(rule.get("requires_human_approval", False)),
        )
        (evaluation.applied if applies else evaluation.not_applied).append(result)
        if unknown:
            for airport in context.unknown_airports:
                name = f"airport_country:{airport}"
                if name not in evaluation.missing_inputs:
                    evaluation.missing_inputs.append(name)
    return evaluation
