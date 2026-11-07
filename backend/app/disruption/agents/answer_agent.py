"""Answer agent built with ADK (task 6.3, design D13).

An `LlmAgent` with the safe facade functions (task 6.1) as its only tools,
no `output_schema` (free-text draft), and a 5 s timeout. The draft always
goes through the deterministic validator (task 6.2) before it can be sent;
on any failure - timeout, error, or a rejected draft - the template answer
is used instead. Every tool call, the validator result and whether the
template fallback was used are recorded in the trace (design D13
traceability requirement).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.disruption.agents.tools import DisruptionToolsFacade
from app.disruption.agents.validator import validate_answer_draft
from app.disruption.contracts import Decision, TraceEntry, TripState

APP_NAME = "nubara-answer-agent"

_INSTRUCTION = (
    "You answer a passenger's question about their flight disruption. Use "
    "the available tools to look up the trip summary, entitlements and "
    "policy rules for THIS request only. Mention only the recommended "
    "option (never any other flight), always include the policy reference, "
    "never invent facts, never claim the booking was changed or that "
    "compensation was approved, and say an agent will follow up when a "
    "human review is required. Never include personal data."
)


def _template_answer(decision: Decision) -> str:
    option = decision.recommended_option
    flight = option.flight_number if option is not None else None
    policy_ref = decision.policy_ref or "the applicable policy"
    lines = [f"We found a change affecting your trip, evaluated under {policy_ref}."]
    if flight:
        lines.append(f"We can offer {flight} as a replacement.")
    if decision.requires_human:
        lines.append("An agent will review and confirm this with you shortly.")
    return " ".join(lines)


class ToolCallRecorder:
    def __init__(self, facade: DisruptionToolsFacade):
        self._facade = facade
        self.calls: list[dict] = []

    def _wrap(self, name: str, fn):
        def wrapped(*args, **kwargs):
            started = time.monotonic()
            result = fn(*args, **kwargs)
            self.calls.append(
                {
                    "tool": name,
                    "args": kwargs or (args if args else {}),
                    "latency_ms": (time.monotonic() - started) * 1000,
                }
            )
            return result

        wrapped.__name__ = name
        wrapped.__doc__ = fn.__doc__
        return wrapped

    def tools(self) -> list:
        return [
            self._wrap("get_trip_summary", self._facade.get_trip_summary),
            self._wrap("get_entitlements", self._facade.get_entitlements),
            self._wrap("get_policy_rule", self._facade.get_policy_rule),
        ]


@dataclass
class AnswerAgentResult:
    message: str
    fallback_used: bool
    trace: TraceEntry
    draft_trace: list[TraceEntry] = field(default_factory=list)


class AnswerAgentRunner:
    """Real ADK-backed runner, used when `use_fake` callers are not injected."""

    def __init__(self, model: str, api_key: str | None, timeout_seconds: float = 5.0):
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def _run(self, question: str, recorder: ToolCallRecorder) -> str:
        import os

        if self.api_key:
            os.environ.setdefault("GOOGLE_API_KEY", self.api_key)

        agent = LlmAgent(
            name="answer_agent",
            model=self.model,
            instruction=_INSTRUCTION,
            tools=recorder.tools(),
            timeout=self.timeout_seconds,
        )
        session_service = InMemorySessionService()
        user_id = "answer"
        session = await session_service.create_session(app_name=APP_NAME, user_id=user_id)
        runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)
        message = types.Content(role="user", parts=[types.Part(text=question)])

        final_text: str | None = None
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text

        if not final_text:
            raise RuntimeError("answer_agent produced no output")
        return final_text

    def draft(self, question: str, recorder: ToolCallRecorder) -> str:
        return asyncio.run(asyncio.wait_for(self._run(question, recorder), timeout=self.timeout_seconds))


def answer_question(
    question: str,
    trip: TripState,
    decision: Decision,
    *,
    model: str,
    api_key: str | None,
    timeout_seconds: float = 5.0,
    agent_runner: AnswerAgentRunner | None = None,
    fallback_message: str | None = None,
) -> AnswerAgentResult:
    """Draft a passenger answer and validate it, falling back to the
    template on any timeout, error, or validation failure.

    `agent_runner` is an injection point for tests: pass a fake with a
    `.draft(question, recorder)` method to avoid real model calls.
    `fallback_message` lets the caller supply the real, deterministic
    template text (design D13's "template answer") built for this decision
    (e.g. from `communication.messages.build_message`); when omitted, a
    minimal built-in template is used instead (kept for callers/tests that
    do not build a full `PassengerMessage`).
    """
    facade = DisruptionToolsFacade(trip, decision)
    recorder = ToolCallRecorder(facade)
    runner = agent_runner or AnswerAgentRunner(model=model, api_key=api_key, timeout_seconds=timeout_seconds)
    template_text = fallback_message if fallback_message is not None else _template_answer(decision)

    fallback_used = False
    fallback_reason: str | None = None
    validator_result = None
    message: str

    try:
        draft = runner.draft(question, recorder)
        validator_result = validate_answer_draft(draft, decision)
        if validator_result.accepted:
            message = draft
        else:
            fallback_used = True
            fallback_reason = validator_result.reason
            message = template_text
    except Exception as exc:  # noqa: BLE001 - any agent failure degrades to the template
        fallback_used = True
        fallback_reason = type(exc).__name__
        message = template_text

    trace = TraceEntry(
        step="answer_agent",
        message=f"answer_agent: fallback_used={fallback_used}",
        data={
            "framework": "google-adk",
            "agent": "answer_agent",
            "tool_calls": recorder.calls,
            "validator_result": {
                "accepted": validator_result.accepted if validator_result else None,
                "reason": validator_result.reason if validator_result else fallback_reason,
            },
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
        },
    )
    return AnswerAgentResult(message=message, fallback_used=fallback_used, trace=trace)
