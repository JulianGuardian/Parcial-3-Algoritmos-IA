"""Save one full-run trace of the target conversation (task 5.3).

Standalone script (not a pytest case): runs the two-turn ABC123 target
conversation against the real model and writes the combined JSON-lines
trace to `docs/trace-abc123.jsonl`. Run from `backend/`:

    EVAL_INTENT_MODEL=<a model confirmed reachable> python -m evals.save_trace

Requires `INTENT_MODEL_API_KEY`. Uses the same longer timeouts as the
evaluation cases (a free-tier model under load can be far slower than the
production default), and never includes personal data (the trace only
ever carries tool names, arguments and outcomes - see `agents/workflow.py`).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

from google.adk.sessions import InMemorySessionService

from app.core.config import Settings, get_settings
from app.disruption.actions.write_tools import MockWriteTools
from app.disruption.agents.disruption_tools import ToolDeps
from app.disruption.agents.workflow import APP_NAME, run_turn

NOW = "2026-09-15T11:03:00Z"
D11_QUESTION = "My flight was delayed. Will I be compensated? Can I still fly today with my son?"
OUT_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "trace-abc123.jsonl"


def main() -> None:
    base = get_settings()
    if not base.intent_model_api_key:
        print("INTENT_MODEL_API_KEY not configured; nothing to run.", file=sys.stderr)
        raise SystemExit(1)

    model = os.environ.get("EVAL_INTENT_MODEL", base.intent_model)
    settings = Settings(
        _env_file=None,
        intent_classifier="adk",
        intent_model_api_key=base.intent_model_api_key,
        intent_model=model,
    )

    session_service = InMemorySessionService()
    conversation_id = uuid.uuid4().hex
    asyncio.run(
        session_service.create_session(
            app_name=APP_NAME,
            user_id=conversation_id,
            session_id=conversation_id,
            state={"booking_id": "ABC123"},
        )
    )
    deps = ToolDeps(write_tools=MockWriteTools())

    def turn(message: str, **kw):
        return run_turn(
            session_service=session_service,
            app_name=APP_NAME,
            user_id=conversation_id,
            session_id=conversation_id,
            booking_id="ABC123",
            message=message,
            deps=deps,
            settings=settings,
            classifier_timeout=45.0,
            agent_timeout=90.0,
            **kw,
        )

    turn1 = turn(D11_QUESTION, now=NOW)
    turn2 = turn("Yes, please book that option for me.", confirm_option_id="O1", now=NOW)

    trace = [*turn1.trace, *turn2.trace]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as fh:
        for entry in trace:
            fh.write(json.dumps(entry) + "\n")

    print(f"model={model} turn1.degraded={turn1.response.degraded} turn2.degraded={turn2.response.degraded}")
    print(f"wrote {len(trace)} lines to {OUT_PATH}")


if __name__ == "__main__":
    main()
