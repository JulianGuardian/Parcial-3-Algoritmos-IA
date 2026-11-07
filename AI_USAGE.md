# AI Usage & Decision Note

## AI tools used

| Tool | What for |
|---|---|
| Claude Code (Claude Sonnet 5 / Opus 5.5) | Reading the exam statement; resolving ambiguities; drafting both OpenSpec changes (proposal, specs, design, tasks); transcribing sample responses into fixtures; implementing and testing the deterministic core (1.x–3.x), the first `intent_classifier`/`answer_agent` pair, and Part B's `disruption_agent` workflow, guardrails, conversation API and real-model evaluations. |
| Google ADK 2.13 (`google-adk`) | The runtime for every agent: `LlmAgent`, `SequentialAgent`, function-calling tools, `before_tool_callback`, sessions. |
| OpenSpec CLI (not a model) | Spec-driven structure, `openspec validate --strict`, task tracking across both changes. |

In the product, AI appears only where free text must be understood or worded (design D11–D13 of the first change; D1, D5, D7 of `build-disruption-agent`). `intent_classifier` turns a question into a closed set of intents, with no tools. `disruption_agent` chooses among guarded read/write tools over the deterministic core and drafts the reply, which a code validator checks before it is sent. Every rule, filter, write and escalation decision is deterministic; a model failure degrades to the keyword classifier, the deterministic pipeline and the template reply rather than failing the request.

## Outputs accepted, modified or rejected

- **Accepted, after checking by hand against the statement:**
  - the reading of ABC123: a missed connection gives R3; R1 and R2 do not apply at 160 min; R5 requires a human; O2 fails on seats and fee; E-1012 is discarded;
  - the proposed resolutions of the section 4 ambiguities;
  - the idempotency and 503 strategy.
- **Modified:**
  - the stack, from plain Python 3.11 to Python 3.12 + FastAPI + Docker;
  - the layout, from a new `src/` package to our existing `backend/`;
  - the artifacts, rewritten in English;
  - the agent design, twice: first a read-only `answer_agent` over a sanitized facade, then (Part B) a single `disruption_agent` with guarded write tools behind a `SequentialAgent`, because the exam requires the LLM itself to choose tools and drive a confirm-then-rebook conversation;
  - the first draft of `AgentResponse`, which put `next_step` under the model's judgment; changed so every field but `reply` is computed in code from the turn's tool results.
- **Rejected:**
  - an agent with direct access to the raw exam tools, or any write tool without a code-level guard in front of it;
  - letting free-text "yes" count as a rebooking confirmation (it must be a structured `confirm_option_id`);
  - team and ownership details inside spec files; dropping docker-compose, which we already use.

## How we validated them

- Every spec scenario is backed by a test: `pytest` → 190 passing, 1 skipped (an optional real-model test, skipped without a key). Tests assert no personal data reaches a tool input, a response, a message or the trace.
- Four real-model evaluation cases (`pytest evals -m llm`) check the tool trajectory, the structured response and faithfulness against the live model; results and the model id/date are recorded in `backend/evals/results/latest.json`, not overwritten when a run is entirely blocked by quota. A full conversation trace is saved to `docs/trace-abc123.jsonl` and scanned for personal data.
- `openspec validate --all --strict` passes on every change; every diff is reviewed manually before commit.

## Decisions we made personally

- The stack (Python 3.12, FastAPI, Docker, Google ADK) and building on the existing backend skeleton.
- Keeping the LLM out of every decision with cost, compliance or safety consequences: rules, option filtering, confirmation and escalation are enforced in code (`before_tool_callback`, a post-run escalation check), never by instruction alone.
- Degrading to a fully deterministic path (keyword classifier, `resolve_disruption`, template) on any model failure, so a free-tier outage never blocks a passenger.
- Removing the unused `.claude/` folder, and splitting the work among three people.

## Information we would never give to a model

- Identity documents, full emails, phone numbers or surnames of passengers.
- Raw tool responses (unreconciled events, rejected options, superseded policies, source names) - the model only ever sees the whitelisted, reconciled fields in `agents/contracts.py`.
- The raw exam tools or `notify_passenger`; the agent's only write tools are `request_rebooking`/`escalate_to_human`, and neither runs without the code-level checks in `agents/guardrails.py`.
- A booking id or passenger identifier as a tool argument; every tool is bound to the session's own booking.
- API keys, `.env` files or any credential; real customer data (only the exam's fictitious samples were used).
