# Tasks

## 1. Fixtures and deterministic groundwork

- [x] 1.1 Add fixtures for an adult-only booking (`DEF456`: same flights, one adult, so no R5) and for a booking with contradictory trusted sources (`GHI789`: `OPS_CORE` CANCELLED vs `AIRPORT_FEED` DELAYED), register them in the read adapters, and verify that loader tests return both
- [x] 1.2 Split `actions/service.py` into single-action functions (`rebook_option(decision, option_id, tools)` and `open_human_case(reasons, decision, state, tools)`), reusing the idempotency and 503 logic, and verify that the existing action tests still pass against the new functions
- [x] 1.3 Stop `execute_actions` from auto-creating rebookings (it only escalates now), and verify a test where DEF456 without confirmation makes no `create_rebooking_request` call and `next_step` would be `CONFIRM_OPTION`

## 2. Agent tools and guardrails

- [x] 2.1 Implement typed, whitelisted read tools `get_trip_status`, `get_entitlements` and `get_policy_rule` over the core, reading the booking and the intake flags from `tool_context.state`, and verify tests for "no tool has an identifier parameter", "no PII or source names in any result" and "an instruction planted in an event field never reaches a result"
- [x] 2.2 Implement the write tools `request_rebooking(option_id)` and `escalate_to_human(reason)` (closed reason enum, evidence built in code), and verify that an invalid reason is rejected without creating a case
- [x] 2.3 Implement `before_tool_callback` (confirmation, re-validation at the current time, human gate), and verify tests for `NOT_CONFIRMED`, `OPTION_NOT_VALID`, "blocked when a human is required" and "confirmed and valid → exactly one rebooking with the deterministic key"
- [x] 2.4 Implement the post-run escalation enforcement (`escalation_enforced_by_code`), and verify a test where a run without `escalate_to_human` still yields exactly one case for ABC123

## 3. Agent workflow and structured response

- [x] 3.1 Build the `SequentialAgent` `disruption_companion` with `intent_classifier` (`output_key="intake"`, reusing the existing classifier definition) and `disruption_agent` (the tools from group 2, `before_tool_callback`, an instruction that treats tool output as data), and verify with a scripted fake model that the classifier runs before the first tool call
- [x] 3.2 Implement the `AgentResponse` model and the response builder (all fields except `reply` come from the tool results of the turn; `reply` goes through `validate_answer_draft` with the template as fallback), and verify tests for the ABC123 fields (R3 and R5 with `POL-DELAY-2026-03`, only O1, `human_required`, `AGENT_WILL_CONTACT`) and for "reply mentioning NB2450 → template"
- [x] 3.3 Implement degradation (quota, timeout or error → keyword intake, `resolve_disruption`, template; `degraded: true`), and verify a test with a failing fake model where the response matches the deterministic pipeline
- [x] 3.4 Emit the structured JSON-lines trace (agent, tool, arguments, latency, callback decision, request id) and remove the superseded `answer_agent` path, and verify a test that scans a full fake run's trace for personal data

## 4. Conversation API

- [ ] 4.1 Implement `POST /api/v1/conversations` (in-memory ADK session holding the booking id; 201, 404) and `POST /api/v1/conversations/{id}/messages` (`message` 1–500 characters, optional `confirm_option_id` and `now`; 404 `CONVERSATION_NOT_FOUND`, 422, 503 with request id), and verify `TestClient` tests with a fake model
- [ ] 4.2 Verify with `TestClient` and a fake model the two-turn ABC123 conversation (turn 2 with `confirm_option_id=O1` → a human case, no rebooking), and that free-text "book O1" without `confirm_option_id` creates nothing
- [ ] 4.3 Document `GOOGLE_API_KEY` and the free-tier model in `.env.example` (placeholders only), and verify that `docker compose up --build` serves both new endpoints and still starts without a key, in degraded mode

## 5. Evaluation and observability

- [x] 5.1 Implement the faithfulness check (every entitlement maps to an applied rule and a returned `policy_ref`; every flight in the reply is in `options`), and verify that it fails on a response listing an unbacked `MEAL_VOUCHER`
- [ ] 5.2 Add the four real-model evaluation cases under `backend/evals/` (`pytest -m llm`: target conversation, contradictory sources GHI789, malicious input, failed write DEF456 with two 503), each asserting the trajectory, the `AgentResponse` and faithfulness, and verify that they run and write `backend/evals/results/latest.json` with the model id and date (not overwritten on quota errors)
- [ ] 5.3 Save one full-run trace of the target conversation to `docs/trace-abc123.jsonl`, and verify that the PII scan test passes on the saved file
- [ ] 5.4 Write the evaluation report section (latest results or the labeled saved run, and at least one failure the checks revealed or a stated limit of what they prove), and verify that it cites the results file

## 6. Deliverables

- [ ] 6.1 Update `README.md` (≤ 2 pages): problem and expected outcome; assumptions and scope, including the resolved ambiguities; the B(a) architecture with the diagram; answers to Part A items 1–4 (design D8, D7, D3, D9); decisions and discarded alternatives; risks and next steps; validation; and run instructions for local, Docker and evaluations. Verify that the commands run as written
- [ ] 6.2 Update `AI_USAGE.md` (≤ 1 page) for Part A item 5 with the Part B work, and verify that it still fits on one page and covers every required section

## Workflow follow-up

- Archive the change with `openspec archive build-disruption-agent` after the team reviews the implementation.
