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
- **The frontend is a pure UI mock.** `frontend/` renders the chat and the decision card against example data; it makes no API call yet. Wiring it to `/api/v1/conversations` is a later change.
- Next steps: a persistent session store (today: in-memory only, lost on restart), more policy scenarios beyond `DELAY`, and a judge-free automated faithfulness score across more paraphrases of the target question.

## Validation

- **Unit/offline tests:** `pytest` → 190 passed, 1 skipped (an optional real-model intent-classifier test, skipped without a key). No test here calls a real model.
- **Real-model evaluations** (`pytest evals -m llm`, needs `INTENT_MODEL_API_KEY`): four cases - the target conversation, contradictory sources (`GHI789`), a prompt-injection attempt, and a failed write with two `503`s (`DEF456`) - each asserting the tool trajectory, the `AgentResponse`, and faithfulness (every entitlement/`policy_ref` in the response is backed by a tool result; every flight mentioned is one of the options or the passenger's own segment). Latest run (`backend/evals/results/latest.json`, model `gemini-flash-lite-latest`, 2026-11-07): **2 of 4 cases passed live** (`target_conversation_abc123`, `contradictory_sources_ghi789`) with a real, verified tool trajectory and faithfulness held in both; **2 cases failed because the model call degraded** (free-tier `503`/`429` at the time), which the harness reports rather than silently passing or overwriting the file with an all-degraded run. This is the stated limit of what these checks prove: they confirm the guardrails and the deterministic fallback hold under both live and failed model calls, but a given run's live-model coverage is capped by free-tier availability at that moment.
- **Saved trace:** `docs/trace-abc123.jsonl`, a full two-turn live run (classifier -> tools -> guardrail decisions -> reply validation for both turns), scanned for personal data by `tests/disruption/test_saved_trace.py`. It shows the callback correctly blocking `request_rebooking` with `HUMAN_REQUIRED` even on the confirmed turn, since R5 always needs a human for `ABC123`.
- **Frontend:** `pnpm run test` (Vitest) and `pnpm run build` (type-check + production build) in `frontend/`; see `frontend/README.md`.

## Frontend (React + Vite)

The passenger chat lives in `frontend/` (React 19, TypeScript, Vite, MUI, pnpm). It shows the conversation and, under each assistant answer, a card that explains the disruption: what happened to each flight, the passenger's benefits, the proposed option at no extra cost and whether an agent will follow up. The card shows only what a passenger may see.

The screen is a pure UI for now (see Risks above): it makes no API call and shows example data shaped like the response of `POST /api/v1/disruptions/{booking_id}/resolve`. The interface text is in English and the theme follows the system's light or dark preference. More details in [`frontend/README.md`](frontend/README.md).

## How to run

### Requirements

| Tool | Version | Needed for |
|------|---------|------------|
| Git | any | cloning the repo |
| Docker Desktop (or Docker Engine + Compose v2) | Compose ≥ 2.24 | running with Docker |
| Python | 3.12 or higher | running the backend without Docker and its tests |
| Node.js + pnpm | 24.22.1 or newer in 24.x, pnpm 10.33.0 | running the frontend without Docker and its tests |

You do not need to install Python or Node.js if you run with Docker.

### Backend, local (no Docker)

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

This starts two services:

| Service | URL | Notes |
|---------|-----|-------|
| `backend` | <http://localhost:8000> (docs at <http://localhost:8000/docs>) | FastAPI; `backend/app` is mounted, so saving a file reloads it. Serves `GET /health`, `POST /api/v1/disruptions/{booking_id}/resolve`, `POST /api/v1/conversations` and `POST /api/v1/conversations/{id}/messages`, with no key required (degraded mode) |
| `frontend` | <http://localhost:5173> | Vite dev server; `frontend/` is mounted, so saving a file updates the page without a rebuild |

- The first start is slower: it downloads the Node image and installs the frontend dependencies inside the container.
- The container uses its own `node_modules` (a Docker volume), never the one on your machine. If you change dependencies in `frontend/package.json`, restart the service (`docker compose restart frontend`) and it installs what the lockfile says.
- To start only one service: `docker compose up --build backend` or `docker compose up --build frontend`.
- To run it in the background: `docker compose up --build -d`, and follow the logs with `docker compose logs -f frontend` (or `backend`).
- To stop it: `Ctrl+C` (or `docker compose down` if you used `-d`). To also reset the frontend dependencies, use `docker compose down -v`.
- On Linux the container user (uid 1000) must be able to write in `frontend/`; if your user has a different uid, set `user` for the service in a local compose override.
- To use the real model in the backend, put `INTENT_CLASSIFIER=adk` and `INTENT_MODEL_API_KEY=...` in a `.env` file at the repo root.

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

### Frontend, local (no Docker)

Needs Node.js 24.22.1 or newer in the 24.x line and pnpm (see `frontend/.nvmrc`):

```bash
cd frontend
pnpm install
pnpm run dev        # http://localhost:5173
pnpm run test       # unit and component tests
pnpm run build      # type-check and production build
```

### Check that it works

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Or open <http://localhost:8000/docs> in your browser, and <http://localhost:5173> for the frontend. To see the `X-Request-ID` header in the response:

```bash
curl -i -H "X-Request-ID: my-test-1" http://localhost:8000/health
```

### Configuration

Environment variables (see `.env.example`):

| Variable | Values | Default |
|----------|--------|---------|
| `APP_NAME` | text | `nubara-backend` |
| `ENVIRONMENT` | `local`, `staging`, `production` | `local` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `API_V1_PREFIX` | path | `/api/v1` |
| `INTENT_CLASSIFIER` | `keyword`, `adk` | `keyword` |
| `INTENT_MODEL` | a Gemini model id | `gemini-3.8-flash` |
| `INTENT_MODEL_API_KEY` / `GOOGLE_API_KEY` | a free-tier key from AI Studio | unset (degraded mode) |

An invalid value makes the service fail at startup and name the offending variable.

### Troubleshooting

| Symptom | Cause and fix |
|---------|---------------|
| `failed to connect to the docker API` | Docker Desktop is not running. Open it and wait for "Engine running". |
| `port is already allocated` / port 8000 in use | Another process is using port 8000. Stop it or change the mapping in `docker-compose.yml` (for example `"8001:8000"`). |
| Port 5173 in use (the frontend exits with `Port 5173 is already in use`) | Another Vite or tool uses 5173. Stop it or change the mapping in `docker-compose.yml`. |
| `ERR_PNPM_...` in `docker compose logs frontend`, or a dependency that is missing | The `frontend_node_modules` volume is out of date or was interrupted. Run `docker compose down -v` and start again. |
| `ValidationError ... log_level` at startup | Invalid value in `.env`. Use one of the values in the configuration table. |
| `env_file ... required` not supported | Old Compose version. Update Docker Desktop (Compose ≥ 2.24). |
| Reload does not detect changes on Windows | Both services use a polling reloader because file events do not cross the Windows mount; wait 1–2 seconds after saving. |
