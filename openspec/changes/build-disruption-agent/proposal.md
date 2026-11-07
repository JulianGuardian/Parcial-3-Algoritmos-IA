# Proposal

## Why

Part B of the exam makes the agent mandatory: an LLM must interpret the passenger's message and choose the tools through function calling. Today the deterministic pipeline decides and acts on its own, and the answer agent only reads a facade afterwards. That flow cannot hold a conversation, cannot create a rebooking after the passenger confirms, and returns no structured response. It also has no trajectory evaluations and no saved trace.

## What Changes

- Turn the two existing ADK agents into one workflow: a `SequentialAgent` runs `intent_classifier` and then `disruption_agent`. `disruption_agent` is a function-calling agent; it chooses among the read tools built over the deterministic core and two guarded write tools, `request_rebooking` and `escalate_to_human`.
- Enforce the controls in code, with ADK `before_tool_callback` and a post-run check:
  - a rebooking is created only after the passenger confirms an option that is still valid;
  - cases a policy rule reserves for a person always reach `create_human_case`;
  - tool content is treated as data;
  - a `503` never produces a duplicate booking or a false confirmation.
- Return a validated structured response with `what_happened`, `entitlements`, `options`, `next_step`, `policy_refs` and `human_required`, plus a passenger reply. The fields are built in code from the tool results; the LLM only writes the reply, which is validated.
- Add a conversational API (start a conversation, then send messages, optionally confirming an option) on a free-tier Gemini model. The keyword classifier, the deterministic pipeline and the template message act as fallbacks.
- Add at least four evaluation cases that check both the tool trajectory and the answer, a faithfulness check, and a full-run trace with no personal data. Record their latest results, or a saved run when the model quota runs out.
- **BREAKING (spec-level):** the answer agent is no longer read-only. It gains guarded write tools.

## Capabilities

### New Capabilities

- `disruption-agent`: the two-agent ADK workflow, tool selection through function calling, least-privilege tools bound to the session's booking, tool results as data, the structured response contract, and degradation when the model fails.
- `agent-tool-guardrails`: code-level enforcement before and after tool calls: confirmation and validity before rebooking, mandatory escalation for human-reserved cases, and truthful handling of failed writes.
- `agent-conversation-api`: HTTP endpoints to start a conversation for a booking and to exchange messages, including an explicit option confirmation.
- `agent-evaluation`: evaluation cases with trajectory and answer checks, the faithfulness check, the PII-free trace artifact, and the reporting of results and limits.

### Modified Capabilities

- `passenger-answer-agent`: the "Sanitized read-only tools" requirement is removed, because the agent now has guarded write tools; its replacement lives in `disruption-agent` and `agent-tool-guardrails`.
- `controlled-actions`: adds the requirement that a rebooking is requested only for an option the passenger explicitly confirmed and that is still valid.

## Impact

- **New code** in `backend/app/disruption/agents/`: the workflow, the tool set, the callbacks and the response builder. It also adds `backend/app/api/v1/conversations.py` and evaluation suites under `backend/evals/`.
- **Reused:** assessment, entitlements, actions, messages, the validator, the keyword classifier, the fixtures and contracts.
- **Refactored:** `actions/service.py`, so a single action (rebook one option, or open one case) can be called by a tool.
- **New fixtures** for an adult-only booking and for a booking with contradictory sources, both used by the evaluations.
- **Model:** a free-tier Gemini model through Google AI Studio. The key lives only in `.env` and is never committed.
- **Docs:** the README gains the architecture, the diagram and the answers to Part A items 1–4. `AI_USAGE.md` is updated for item 5.
