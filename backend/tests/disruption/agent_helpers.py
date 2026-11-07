"""Helpers shared by the agent-tool tests (no model is ever called)."""

from types import SimpleNamespace

from app.disruption.actions.write_tools import MockWriteTools
from app.disruption.agents.contracts import STATE_BOOKING_ID, STATE_CONFIRMED_OPTION, STATE_INTAKE, STATE_NOW
from app.disruption.agents.disruption_tools import ToolDeps, build_tools

NOW = "2026-09-15T11:03:00Z"
PII = ("12.345.678-9", "maria.silva@example.com", "8765 4321", "Silva", "document_id", "98.765.432-1", "Pérez")


class FakeToolContext:
    """Stands in for ADK's ToolContext: tools only use `.state`."""

    def __init__(self, state):
        self.state = state


def session(booking_id="ABC123", *, confirmed=None, compensation=False, now=NOW):
    state = {
        STATE_BOOKING_ID: booking_id,
        STATE_NOW: now,
        STATE_INTAKE: {"intents": ["TRIP_STATUS"], "compensation_requested": compensation, "wants_same_day": False},
    }
    if confirmed:
        state[STATE_CONFIRMED_OPTION] = confirmed
    return state


def toolkit(write_tools=None, **deps_kwargs):
    deps = ToolDeps(write_tools=write_tools or MockWriteTools(), **deps_kwargs)
    tools = {fn.__name__: fn for fn in build_tools(deps)}
    return deps, tools


def tool(name):
    return SimpleNamespace(name=name)
