# Nubara Disruption Companion

Third midterm project for the Algorithms - Artificial Intelligence course.
Repository: <https://github.com/JulianGuardian/Parcial-3-Algoritmos-IA>

## Problem and expected outcome

A passenger whose flight was disrupted needs to know what happened and what to do next, without being given unverified information and without the system executing a high-impact action (rebooking, compensation) on its own. The outcome is a backend that: (1) resolves a disruption deterministically from the exam's mock tools, and (2) lets a passenger hold a short conversation with an LLM-driven agent that reads the same deterministic core through guarded tools, explains the situation, and can request a rebooking only once the passenger has explicitly confirmed it.

## Assumptions and scope

- Single scenario (`DELAY`), single policy version, bookings `ABC123`/`DEF456`/`GHI789` from the fixtures.
- No UI, no persistent sessions (conversations live only in process memory), no authentication, no real airline systems.
- **Resolved ambiguity:** the exam's "target conversation" text was not in the material received; we assume turn 1 is the multi-intent question from design D11 ("My flight was delayed. Will I be compensated? Can I still fly today with my son?") and turn 2 confirms option O1. This is documented in `design.md`'s Open Questions and does not change the architecture.
- Compensation (R4) and any case a policy rule reserves for a human always go to `create_human_case`; the agent never approves or promises an outcome.

## Architecture (Part B(a))

```
 passenger message (+ confirm_option_id, redacted in code)
                    |
   SequentialAgent "disruption_companion"
   +----------------------+   state["intake"]   +--------------------+
   | intent_classifier    | ------------------> | disruption_agent   |
   | LlmAgent, no tools    |   (output_key)      | LlmAgent, function |
   | closed output_schema  |                     | calling (ReAct)    |
   +----------------------+                     +---------+----------+
                                                            | before_tool_callback
         +------------------+------------------+-----------+------------+-----------------+
         v                  v                  v                        v                 |
  get_trip_status    get_entitlements    get_policy_rule          request_rebooking   escalate_to_human
   (assessment)        (entitlements)      (current policy)         (guarded)        (closed reasons)
                                                                        |                   |
                                                                        v                   v
                                                           create_rebooking_request   create_human_case
                            |
         after the run: enforce escalation -> build AgentResponse -> validate reply -> notify
```

Two agents, not one: the agent that reads raw passenger text has no tools, so a prompt injection can at most change an intent flag. The tool-calling agent never sees the raw text, only validated flags and read-only facts; the four Part B(c) controls (confirmation, mandatory escalation, tool output as data, truthful 503 handling) run in code (`agents/guardrails.py`), not in the prompt. Full rationale: `design.md` D1-D5.

## Part A answers

1. **Autonomy boundary (D8).** The LLM may only: classify text into a closed intent set, and choose which read tools to call and when to escalate. It may never: add intents, decide entitlements, call a raw exam tool, pass a booking id, or rebook without a confirmed+valid option. Rules, options and the structured response fields are always computed in code; only the reply's wording is the model's.
2. **Model, cost, value and degradation (D7).** A free-tier Gemini model (`INTENT_MODEL`, confirmed in AI Studio). ~3-5 LLM calls per turn (classifier, 1-3 tool rounds, final reply). On a timeout, quota error or any model failure, the service falls back to the keyword classifier, the deterministic `resolve_disruption` pipeline and the template reply, and marks the response `degraded: true` - it never fails the request. The agent's value over a fixed pipeline is handling free-form, multi-intent questions and driving the confirm-then-rebook conversation; every fact and every write stays deterministic.
3. **Personal data (D3).** The model only ever sees: the lead passenger's first name, party size, `has_minor`, flight numbers/airports/times, and fare family/`changeable`/`refundable`. It never sees `document_id`, email, phone, surname, loyalty tier, raw events, discarded events or rejected-option detail. Enforced in `assessment/privacy.py`, the typed tool-result models (whitelisted fields), `redact()` on the incoming message, and a test that scans tool inputs and the trace for personal data (`tests/disruption/test_workflow.py`, `tests/disruption/test_saved_trace.py`).
4. **Tools over RAG for policy (D9).** Policy rules are versioned, few and must be applied exactly, with an auditable `policy_ref` on every entitlement; a vector store could surface a similar-but-superseded or unrelated rule ranked by similarity rather than validity. RAG would be justified for long, non-decisional passenger guidance (general-rights FAQs), never for anything that feeds an entitlement.

## Decisions and discarded alternatives

- `SequentialAgent` over a single agent or `sub_agents` transfer: the order (classify, then act) never changes, needs no extra LLM routing call, and keeps the write-capable agent away from raw text.
- Guardrails in code (`before_tool_callback` + a post-run escalation check), not in the prompt: the real guarantee that a rebooking needs confirmation, or that a human case always opens when policy requires it, cannot depend on the model following an instruction.
- The structured response (`AgentResponse`) is built entirely in code from the turn's tool results, except `reply`; `output_schema` on the tool-calling agent was rejected because ADK does not combine it with tools, and because model-filled structured fields could be wrong.
- `request_rebooking`/`escalate_to_human` over letting the agent call the raw exam write tools directly: evidence and idempotency keys are built in code, never trusted from the model.

## Risks and next steps

- **Free-tier availability.** During this session, `gemini-3.8-flash` and `gemini-3-flash-preview` returned `503`/`429` under real load; `gemini-flash-lite-latest` was reachable. `INTENT_MODEL` is a setting precisely so the deployed model can be swapped without a code change, and degradation ensures the service stays correct either way.
- **A confirmed rebooking can still be blocked.** The callback re-validates the option against a fresh `decide()` call at request time; an option that expired or whose party no longer fits is refused with a typed reason, not silently retried.
- Next steps: a persistent session store (today: in-memory only, lost on restart), more policy scenarios beyond `DELAY`, and a judge-free automated faithfulness score across more paraphrases of the target question.

## Validation

- **Unit/offline tests:** `pytest` → 190 passed, 1 skipped (an optional real-model intent-classifier test, skipped without a key). No test here calls a real model.
- **Real-model evaluations** (`pytest evals -m llm`, needs `INTENT_MODEL_API_KEY`): four cases - the target conversation, contradictory sources (`GHI789`), a prompt-injection attempt, and a failed write with two `503`s (`DEF456`) - each asserting the tool trajectory, the `AgentResponse`, and faithfulness (every entitlement/`policy_ref` in the response is backed by a tool result; every flight mentioned is one of the options or the passenger's own segment). Latest run (`backend/evals/results/latest.json`, model `gemini-flash-lite-latest`, 2026-11-07): **2 of 4 cases passed live** (`target_conversation_abc123`, `contradictory_sources_ghi789`) with a real, verified tool trajectory and faithfulness held in both; **2 cases failed because the model call degraded** (free-tier `503`/`429` at the time), which the harness reports rather than silently passing or overwriting the file with an all-degraded run. This is the stated limit of what these checks prove: they confirm the guardrails and the deterministic fallback hold under both live and failed model calls, but a given run's live-model coverage is capped by free-tier availability at that moment.
- **Saved trace:** `docs/trace-abc123.jsonl`, a full two-turn live run (classifier -> tools -> guardrail decisions -> reply validation for both turns), scanned for personal data by `tests/disruption/test_saved_trace.py`. It shows the callback correctly blocking `request_rebooking` with `HUMAN_REQUIRED` even on the confirmed turn, since R5 always needs a human for `ABC123`.

## How to run

### Requirements

Git; Docker Desktop (Compose ≥ 2.24) or Python 3.12+ to run without Docker.

### Local (no Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows; Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Service at <http://127.0.0.1:8000>, docs at `/docs`. Copy `backend/.env.example` to `backend/.env` to set `INTENT_CLASSIFIER=adk` and `INTENT_MODEL_API_KEY` (get a free-tier key at <https://aistudio.google.com/apikey>); with no key the service still runs, in degraded mode.

### Docker

```bash
docker compose up --build
```

Serves `GET /health`, `POST /api/v1/disruptions/{booking_id}/resolve`, `POST /api/v1/conversations` and `POST /api/v1/conversations/{id}/messages` at <http://localhost:8000>, with no key required (degraded mode). To use the real model in Docker, put `INTENT_CLASSIFIER=adk` and `INTENT_MODEL_API_KEY=...` in a `.env` file at the repo root.

Try the conversational agent:

```bash
curl -s -X POST localhost:8000/api/v1/conversations -H "Content-Type: application/json" -d '{"booking_id":"ABC123"}'
# {"conversation_id": "...", "booking_id": "ABC123"}
curl -s -X POST localhost:8000/api/v1/conversations/<id>/messages -H "Content-Type: application/json" \
  -d '{"message":"What happened to my flight?","now":"2026-09-15T11:03:00Z"}'
```

### Tests and evaluations

From `backend/`, with the virtual environment active:

```bash
pytest                                        # unit/offline suite, no model or network needed
EVAL_INTENT_MODEL=gemini-flash-lite-latest pytest evals -m llm   # real-model cases; needs INTENT_MODEL_API_KEY
python -m evals.save_trace                    # regenerates docs/trace-abc123.jsonl against the real model
```

`EVAL_INTENT_MODEL` is optional; it only overrides which model the evaluations target, in case the app's default is temporarily unavailable on the free tier.
