"""Helpers shared by the agent-tool tests (no model is ever called)."""

import asyncio
from types import SimpleNamespace

from google.adk.models import BaseLlm, LlmResponse
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.disruption.actions.write_tools import MockWriteTools
from app.disruption.agents.contracts import STATE_BOOKING_ID, STATE_CONFIRMED_OPTION, STATE_INTAKE, STATE_NOW
from app.disruption.agents.disruption_tools import ToolDeps, build_tools

NOW = "2026-09-15T11:03:00Z"
PII = ("12.345.678-9", "maria.silva@example.com", "8765 4321", "Silva", "document_id", "98.765.432-1", "Pérez")


class FakeLlm(BaseLlm):
    """A scripted `BaseLlm`: each call returns the next response in `script`.

    Drives the real ADK `Runner`/`SequentialAgent` machinery (tool dispatch,
    `before_tool_callback`, session state) without any network call.
    """

    model: str = "fake-model"
    script: list = []
    fail_after: int | None = None

    def __init__(self, script, **kwargs):
        super().__init__(script=script, **kwargs)
        self._calls = 0

    async def generate_content_async(self, llm_request, stream: bool = False):
        if self.fail_after is not None and self._calls >= self.fail_after:
            raise RuntimeError("simulated model failure")
        response = self.script[self._calls]
        self._calls += 1
        yield response

    @property
    def call_count(self) -> int:
        return self._calls


def text_response(text: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]), turn_complete=True)


def call_response(name: str, args: dict) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))]))


def new_session_service(booking_id="ABC123", *, confirmed=None, now=NOW):
    """An `InMemorySessionService` with one session already holding state."""
    service = InMemorySessionService()
    state = {STATE_BOOKING_ID: booking_id, STATE_NOW: now}
    if confirmed:
        state[STATE_CONFIRMED_OPTION] = confirmed
    session = asyncio.run(
        service.create_session(app_name="test-app", user_id="u1", session_id="s1", state=state)
    )
    return service, session


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
