"""Shared fixtures for the real-model evaluation cases (task 5.2).

Run with `pytest evals -m llm` from `backend/`. Every case is skipped at
collection time when no model key is configured, so a plain `pytest` run
(which does not pass `-m llm`, and does not look under `evals/` at all per
`testpaths` in `pyproject.toml`) is never affected by this directory.
"""

from __future__ import annotations

import uuid

import pytest
from google.adk.sessions import InMemorySessionService

from app.core.config import Settings, get_settings
from app.disruption.actions.write_tools import MockWriteTools
from app.disruption.agents.disruption_tools import ToolDeps
from app.disruption.agents.workflow import APP_NAME, run_turn
from evals.report import CaseResult

# A free-tier model under load can take far longer than the passenger-facing
# default (design D12/D13's 3 s/5 s); give it real room before degrading.
CLASSIFIER_TIMEOUT = 45.0
AGENT_TIMEOUT = 90.0

_settings = get_settings()
requires_model_key = pytest.mark.skipif(
    not _settings.intent_model_api_key,
    reason="INTENT_MODEL_API_KEY not configured; real-model evaluations need a key",
)

_collected: list[CaseResult] = []
_model_id: str | None = None


def record(result: CaseResult, *, model: str) -> None:
    global _model_id
    _model_id = model
    _collected.append(result)


def run_case(name: str, fn, *, model: str):
    """Run one eval case and record its `CaseResult` regardless of outcome.

    `fn()` must return `(outcome, faithfulness_result_or_None, notes)` after
    making its own assertions; those assertions may raise `AssertionError`,
    in which case the case is recorded as failed (and, conservatively,
    degraded) before the error is re-raised so pytest still reports it.
    `model` is the model actually used for this case (the `settings`
    fixture's `intent_model`, which may be overridden by `EVAL_INTENT_MODEL`).
    """
    outcome = None
    faithfulness = None
    notes = ""
    passed = False
    try:
        outcome, faithfulness, notes = fn()
        passed = True
        return outcome
    except AssertionError as exc:
        notes = notes or str(exc)
        raise
    finally:
        record(
            CaseResult(
                name=name,
                degraded=bool(outcome.response.degraded) if outcome else True,
                passed=passed,
                trajectory=list(outcome.response.trajectory) if outcome else [],
                faithfulness_ok=faithfulness.ok if faithfulness else None,
                faithfulness_problems=list(faithfulness.problems) if faithfulness else [],
                notes=notes,
            ),
            model=model,
        )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    from evals.report import save_results

    if _collected:
        save_results(_model_id or "unknown", _collected)


@pytest.fixture
def settings() -> Settings:
    # Overridable per run: the production default (gemini-3.8-flash) was
    # persistently returning 503 UNAVAILABLE (free-tier demand) when these
    # evaluations were last run; EVAL_INTENT_MODEL lets a run target a model
    # confirmed reachable at the time without changing the app's default.
    import os

    model = os.environ.get("EVAL_INTENT_MODEL", _settings.intent_model)
    return Settings(
        _env_file=None,
        intent_classifier="adk",
        intent_model_api_key=_settings.intent_model_api_key,
        intent_model=model,
    )


@pytest.fixture
def new_conversation(settings: Settings):
    """Start a fresh conversation for one booking; returns a `turn(message, **kw)` callable."""

    def _start(booking_id: str, *, write_tools: MockWriteTools | None = None):
        session_service = InMemorySessionService()
        conversation_id = uuid.uuid4().hex
        import asyncio

        asyncio.run(
            session_service.create_session(
                app_name=APP_NAME,
                user_id=conversation_id,
                session_id=conversation_id,
                state={"booking_id": booking_id},
            )
        )
        deps = ToolDeps(write_tools=write_tools or MockWriteTools())

        def turn(message: str, *, confirm_option_id: str | None = None, now: str | None = None):
            return run_turn(
                session_service=session_service,
                app_name=APP_NAME,
                user_id=conversation_id,
                session_id=conversation_id,
                booking_id=booking_id,
                message=message,
                deps=deps,
                settings=settings,
                confirm_option_id=confirm_option_id,
                now=now,
                classifier_timeout=CLASSIFIER_TIMEOUT,
                agent_timeout=AGENT_TIMEOUT,
            )

        return turn, deps

    return _start
