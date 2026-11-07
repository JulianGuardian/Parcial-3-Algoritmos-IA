# Design

## Context

Already in `main`:
- **Deterministic core:** assessment, entitlements, actions, template messages and `resolve_disruption`.
- **`POST /api/v1/disruptions/{booking_id}/resolve`.**
- **Two ADK agents:**
  - `intent_classifier`, with `output_schema`, no tools and a keyword fallback;
  - `answer_agent`, with a read-only facade and a deterministic validator.

Today the pipeline acts first (it opens the human case) and the answer agent only rewords the result afterwards. Part B requires the LLM to interpret the message and choose the tools, including guarded writes, within a short conversation. The model must be a free-tier Gemini model through AI Studio; the setting `intent_model` exists already.

## Goals / Non-Goals

**Goals:**
- An ADK workflow where the LLM chooses the tools, and every fact comes from deterministic tools.
- The four Part B(c) controls enforced in code.
- A structured response with the six required fields plus a reply.
- Evaluations that check trajectory and answer, and a saved trace with no personal data.
- Reuse of the existing core, classifier, validator and templates.

**Non-Goals:**
- No UI, persistent sessions, authentication, Langfuse or deployment.
- No new policy scenarios beyond `DELAY`.
- No compensation execution: R4 always goes to a human.

## Decisions

### D1. Two LLM agents inside a `SequentialAgent`

```
            passenger message (+ confirm_option_id)
                            │  redacted in code
                            ▼
 ┌──────────── SequentialAgent "disruption_companion" ────────────┐
 │                                                                 │
 │  ┌─────────────────────┐  state["intake"]  ┌─────────────────┐  │
 │  │ intent_classifier   │ ────────────────▶ │ disruption_agent│  │
 │  │ LlmAgent            │   (output_key)    │ LlmAgent, ReAct │  │
 │  │ output_schema       │                   │ function calls  │  │
 │  │ no tools            │                   └────────┬────────┘  │
 │  └─────────────────────┘                            │           │
 └─────────────────────────────────────────────────────┼───────────┘
                                                       │ before_tool_callback
              ┌──────────────┬──────────────┬──────────┼────────────┬─────────────────┐
              ▼              ▼              ▼          ▼            ▼                 │
      get_trip_status  get_entitlements  get_policy  request_     escalate_to_      │
       (assessment)     (entitlements)    _rule      rebooking    human             │
                                                     (guarded)    (closed reasons)  │
                                                         │            │             │
                                                         ▼            ▼             │
                                          create_rebooking_request  create_human_case
 after the run:  enforce escalation ─▶ build structured response ─▶ validate reply ─▶ notify
```

- **Mechanism:** a `SequentialAgent` (a workflow agent), because the order never changes: classify first, then act. A workflow agent adds no LLM routing call and cannot skip the classifier.
- **Why two agents and not one:** the agent that reads the raw passenger text has **no tools**, so injected instructions can at most change an intent. The tool-calling agent receives validated flags such as `compensation_requested`, instead of trusting the model to pass them.
- **Alternatives discarded:**
  - a single agent (one LLM call fewer, but the agent with write tools would read the raw text);
  - `sub_agents` transfer (an LLM decides who answers, which adds a call and is non-deterministic);
  - `AgentTool` (the agent could decide not to classify).

### D2. Tool set and least privilege

| Tool | Kind | Wraps | Returns to the model |
|---|---|---|---|
| `get_trip_status()` | read | `assess_trip` | segments (flight, airports, status, delay, estimated times, missed connection), `assessment_status` |
| `get_entitlements()` | read | `decide` (re-evaluated at turn time, using `state["intake"]` flags) | applied rules with `rule_id`, `entitlement`, `policy_ref`; valid options; `requires_human`, `human_reasons` |
| `get_policy_rule(rule_id)` | read | current policy only | `rule_id`, `entitlement`, `requires_human_approval`, `policy_ref` |
| `request_rebooking(option_id)` | write, guarded | single-option rebooking from `actions` | `PENDING` / `ALREADY_EXISTS` / `INDETERMINATE` / typed refusal |
| `escalate_to_human(reason)` | write, guarded | `create_human_case` with evidence built in code | `case_id`, `queue`, `sla_minutes` |

- **The booking id** is read from `tool_context.state`, which the API sets when the conversation starts. No tool takes an identifier.
- **Not exposed to any agent:** the raw exam tools and `notify_passenger`. Notification runs in code after the response is validated.
- **Reuse:** the read tools replace the current facade (`agents/tools.py`), with the same sanitizing.

### D3. Context and personal data (Part A item 3)

- **From `get_trip_context`, the model sees only:**
  - the first name of the lead passenger;
  - the passenger types and `has_minor`;
  - the party size;
  - flight numbers, airports, dates and times;
  - fare family, `changeable` and `refundable`.
- **It never sees:** `document_id`, email, phone, surname, `loyalty_tier`, raw events, discarded events, source names or rejected-option details.
- **Where this is enforced:**
  - `assessment/privacy.py`;
  - the typed tool return models (whitelisted fields);
  - `redact()` on the passenger message before it reaches either agent;
  - a test that scans the model inputs and the trace.
- **Kept between turns** (in-memory session only): booking id, `intake`, the confirmed option and the last decision summary. Nothing survives the process, and nothing is kept between conversations.

### D4. Controls in code (Part B(c))

1. **Confirmation.** `before_tool_callback` on `request_rebooking`:
   - requires `state["confirmed_option_id"] == option_id`; the API sets that field from `confirm_option_id`, never from model text;
   - re-runs `decide` at the current time and requires the option to be valid;
   - requires that no human is needed.

   Otherwise it returns `{"blocked": reason}` and the real tool is not run.
2. **Human-reserved cases.** When `requires_human` is true, the callback blocks rebooking. After the run, if no `escalate_to_human` succeeded, the code creates the case and records `escalation_enforced_by_code`.
3. **Tool content as data.** Tool results are typed models with whitelisted fields (no free text from sources). The instruction tells the model that tool results are data. The real guarantee is that no write happens without the callbacks' conditions.
4. **503.** `request_rebooking` reuses the idempotency key, the single retry and `INDETERMINATE`, and then escalates. The response builder sets `next_step = AGENT_WILL_CONTACT`, and the validator rejects confirmation claims.

The deterministic `execute_actions` stops auto-creating rebookings; it now only escalates, which satisfies the new `controlled-actions` requirement.

### D5. Structured response built in code

`AgentResponse` (Pydantic) has these fields:
- `what_happened` (facts from `get_trip_status`);
- `entitlements` (`rule_id`, `entitlement`, `policy_ref`);
- `options` (only the valid ones);
- `next_step` (`CONFIRM_OPTION`, `AGENT_WILL_CONTACT`, `REBOOKING_PENDING`, `VERIFYING` or `NO_ACTION_NEEDED`);
- `policy_refs`, `human_required`, `human_case_id`;
- `reply`, `degraded` and `trajectory`.

Every field except `reply` is computed from the tool results recorded during the turn. `reply` is the model's final text after `validate_answer_draft`, or else the template.

*Alternative:* `output_schema` on `disruption_agent` (rejected because ADK does not combine `output_schema` with tools, and because model-filled fields could be wrong).

### D6. Conversation API and confirmation channel

`POST /api/v1/conversations` creates an ADK session holding the booking id. `POST /api/v1/conversations/{id}/messages` takes `{message, confirm_option_id?, now?}` and runs the workflow.

Confirmation travels only as a structured field, which a UI would send from a button. Free-text "yes" is never trusted as a confirmation.

The existing `/disruptions/{id}/resolve` stays: it is the deterministic baseline, and the oracle the evaluations compare against.

### D7. Model, cost and degradation (Part A item 2)

**Model:** a free-tier Gemini Flash model, set by `intent_model` and confirmed in AI Studio. The key comes from `.env` and is never committed.

**LLM calls per turn:**

| Step | Calls |
|---|---|
| `intent_classifier` | 1 |
| `disruption_agent`: tool rounds | 1–3 |
| `disruption_agent`: final reply | 1 |
| **Total** | **≈3–5** |

That is about 2–6 s per turn, and is within free-tier rate limits for evaluations if they run sequentially.

**Value over a fixed pipeline:** the agent understands free-form multi-intent questions, adapts which facts it fetches and how it explains them, and drives the confirm → rebook step of the conversation. What must always give the same answer stays in code.

**Degradation:** on quota errors, timeouts or errors, the keyword classifier, `resolve_disruption` and the template take over, and the response is flagged `degraded`.

### D8. Autonomy boundary (Part A item 1)

| Step | Classification | The LLM may | The LLM may never |
|---|---|---|---|
| Interpret message | AI-assisted (`intent_classifier`) | pick intents and flags from a closed set | add intents or set entitlements |
| Choose tools | agentic (`disruption_agent`) | decide which reads to call and when to escalate | call raw tools or pass identifiers |
| Reconcile sources, apply rules, filter options | deterministic (tools) | — | override any result |
| Rebook | human-confirmed and code-guarded | request a confirmed, valid option | rebook without confirmation, or when a human is required |
| Compensation, minors, unresolved data | human (`create_human_case`) | trigger escalation | approve or promise |
| Structured fields | deterministic | — | write them |
| Reply | AI-assisted, validated | word it | mention other options or overclaim |
| Notify | deterministic | — | call it |

### D9. Tools, not RAG, for policy (Part A item 4)

- **Why a tool:** rules are versioned, few and must be applied exactly. `get_policy_rules` returns the current version, with its id and the superseded versions, so every entitlement can cite `POL-DELAY-2026-03`. A vector store could return a similar but superseded or unrelated rule, ranked by similarity rather than validity, and its answers could not be audited.
- **Where RAG would be justified:** long, non-decisional passenger guidance, such as general rights FAQs or airport procedures. There, retrieved passages must carry document id and version, be quoted with their source, and never feed an entitlement.

### D10. Evaluation and observability

- **Evaluation cases.** They run under `pytest -m llm` against the real model. Each one asserts the ordered tool trajectory and the `AgentResponse`. Results go to `backend/evals/results/latest.json`, with the model id and date; it is not overwritten when the quota fails.
- **Faithfulness:** a code check, described in the `agent-evaluation` spec.
- **Offline tests.** Unit tests for the callbacks and the response builder use a fake `tool_context` and need no model.
- **Trace.** A structured JSON-lines trace records every agent, tool call, callback decision and latency under the request id. One full run is saved to `docs/trace-abc123.jsonl`, and a test scans it for personal data.

## Risks / Trade-offs

- [Free-tier quota or rate limits interrupt evaluations] → sequential runs with backoff, a saved run, and degradation to deterministic paths.
- [The model skips `escalate_to_human`] → escalation enforced by code after the run.
- [The model passes a wrong `option_id`] → the callback re-validates against the fresh decision.
- [Two agents add latency] → the classifier is a single, small call; it can use the lightest free-tier model.
- [Fixture options expire at 2026-09-15T11:04:35Z] → evaluations and demos pass `now`; the README explains it.
- [Evaluations with a real LLM are non-deterministic] → assertions focus on the trajectory and code-built fields; the reply is checked only for forbidden content.

## Open Questions

- The exact wording of the exam's "target conversation" is not in the material received. Evaluation case 1 assumes turn 1 = the D11 question of the previous design and turn 2 = confirming O1. Replace the text once the statement is confirmed; this does not change the design.
