# Tasks

## 1. Project setup and shared contracts

- [ ] 1.1 Create the domain package `backend/app/disruption/` (`assessment/`, `entitlements/`, `intake/`, `agents/`, `actions/`, `communication/` and `fixtures/`, each with `__init__.py`) and `backend/tests/disruption/` inside the existing backend, and verify that `pip install -e "backend[dev]"` still succeeds and the existing `pytest` suite still passes
- [x] 1.2 Transcribe the seven sample tool responses from the exam statement into `backend/app/disruption/fixtures/*.json` (see the `README.md` in that folder), and verify each file loads with `json.load`
- [ ] 1.3 Define the `TripState`, `Decision`, `RejectedOption` and `TraceEntry` dataclasses, plus `ResolveRequest`, in `backend/app/disruption/contracts.py` according to design D2, and verify that a test can construct one sample of each

## 2. Trip disruption assessment

- [ ] 2.1 Implement mock read adapters `get_trip_context` and `get_operational_events` that return the fixtures, and verify with a test that they return the contract shapes
- [ ] 2.2 Implement PII stripping (drop `document_id`, mask the email and phone, keep first names), and verify with a test that "12.345.678-9" never appears in `TripState`
- [ ] 2.3 Implement source reconciliation (priority, degraded-source exclusion, recency, `CONFLICTING` on incompatible trusted sources), and verify tests for "E-1012 discarded" and "trusted sources disagree → CONFLICTING"
- [ ] 2.4 Implement the freshness check (configurable maximum age, default 2 h, measured against `_meta.retrieved_at`; `UNVERIFIED` when only stale events exist), and verify tests for "E-1001 is fresh" and "only a stale event → S1 UNVERIFIED and human review required"
- [ ] 2.5 Implement estimated arrival and missed-connection detection with a configurable MCT (default 60), and verify a test where S1 arrives at 20:35 and S2 (19:05) is missed
- [ ] 2.6 Implement relevance classification and `missing_fields` tracking, and verify tests for "missed connection is relevant", "gate change only is informational" and "change_penalty_amount is listed as missing"

## 3. Disruption entitlements

- [ ] 3.1 Implement mock adapters `get_policy_rules` and `get_eligible_options` from the fixtures, and verify with a test that they return the contract shapes
- [ ] 3.2 Implement rule evaluation for R1–R5 using only the current policy version, and verify a test for ABC123 where R3 and R5 apply, R1, R2 and R4 do not apply, and the reasons and `POL-DELAY-2026-03` are recorded
- [ ] 3.3 Implement option filtering (TTL → seats → policy consistency → confidence and evaluated policy) with reason codes, and verify tests where O2 is rejected (`INSUFFICIENT_SEATS`, `POLICY_INCONSISTENT`), O3 is `REQUIRES_AGENT_REVIEW`, and every option is rejected once past the TTL
- [ ] 3.4 Implement recommendation selection and the human-approval gate (`requires_human` for R4, R5, `CONFLICTING` and decision-relevant missing data), and verify a test where ABC123 recommends O1 with `requires_human` true and reason `R5_PRIORITY_HANDLING`, plus a test where `compensation_requested` true adds `R4_CASH_COMPENSATION`

## 4. Passenger query intake

- [ ] 4.1 Define the `IntentResult` Pydantic model (closed `Intent` enum, `compensation_requested`, `wants_same_day`, `confidence`) and the `IntentClassifier` interface, and verify with a test that an intent outside the enum is rejected and mapped to `OTHER`
- [ ] 4.2 Implement question redaction (emails, phone numbers, identity-document patterns) and `KeywordIntentClassifier`, and verify tests for "the multi-intent question from design D11 yields TRIP_STATUS, REBOOK_OPTIONS and COMPENSATION" and "redacted text contains neither maria.silva@example.com nor 12.345.678-9"
- [ ] 4.3 Add a pinned `google-adk` to `backend/pyproject.toml` and implement `AdkIntentClassifier` (an `LlmAgent` named `intent_classifier`, with `output_schema`, no tools, and an ADK `Runner` with `InMemorySessionService`; model and API key from settings; 3 s timeout), and verify that `pip install` succeeds and that an optional integration test, skipped without an API key, returns a valid `IntentResult`
- [ ] 4.4 Implement classifier selection (`INTENT_CLASSIFIER=adk|keyword`), the fallback chain (ADK → keyword → `OTHER` + human) and the trace fields (`framework`, `agent`, `model`, `intents`, `confidence`, `latency_ms`, `fallback_used`), and verify tests with a fake classifier for "timeout → keyword fallback with fallback_used true", "confidence below 0.6 → fallback", "prompt injection only yields COMPENSATION, and R4 still requires a human" and "no question → no classifier call"
- [ ] 4.5 Add `INTENT_CLASSIFIER`, `INTENT_MODEL` and the model API key to the existing `Settings` class and to `.env.example` (placeholders only), extend `tests/test_config.py`, and verify that the service starts with `INTENT_CLASSIFIER=keyword` and no key

## 5. Actions, communication and entry point

- [ ] 5.1 Implement the mock write adapters `create_rebooking_request`, `create_human_case` and `notify_passenger` with injectable 201/409/503/422 responses, and verify with a test that each response can be triggered
- [ ] 5.2 Implement action execution (human case when `requires_human` is true, deterministic idempotency key, 409 reuse, a single 503 retry followed by `REBOOKING_INDETERMINATE` escalation, `PENDING` handling), and verify tests for "ABC123 creates a human case and no rebooking", "R4 + R5 → exactly one human case listing both reasons", "same decision → same key" and "503 twice → exactly 2 calls + human case"
- [ ] 5.3 Implement the template-based passenger message builder (validated facts only, `policy_ref` mandatory, no internal sources or personal data, 422 blocks delivery), and verify tests for "the ABC123 message mentions the delay, the missed NB2410 connection, O1 and agent follow-up, but not ON_TIME or LEGACY_MIRROR", "compensation requested → agent will review it, with no amount or promise" and "422 is recorded and not retried"
- [ ] 5.4 Implement the core function `resolve_disruption(request: ResolveRequest)` in `backend/app/disruption/pipeline.py` that chains assessment → entitlements → actions → communication, and verify with a test that it returns a `Decision` for ABC123
- [ ] 5.5 Implement the route in `backend/app/api/v1/disruptions.py` and mount it on the existing v1 router according to design D10 (`POST /api/v1/disruptions/{booking_id}/resolve` with an optional body `{now, question, compensation_requested}` that runs intake before the pipeline, mapping 200/404/422/503 with the request id, a response model without personal data), and verify `TestClient` tests for "ABC123 → 200 with requires_human true and no document_id", "unknown booking → 404" and "read tool failure → 503 without a stack trace"
- [ ] 5.6 Check the existing Docker setup with the new code (the fixtures ship inside `backend/app`, and `google-adk` installs in the image), and verify that `docker compose up --build` starts healthy and that `curl -X POST localhost:8000/api/v1/disruptions/ABC123/resolve` returns 200

## 6. Passenger answer agent

- [ ] 6.1 Implement the safe read facade `backend/app/disruption/agents/tools.py` (`get_trip_summary`, `get_entitlements`, `get_policy_rule`, bound to the current request with no `booking_id` parameter), and verify tests for "the ABC123 summary has no E-1012, LEGACY_MIRROR or personal data", "entitlements show O1, R3, R5 and POL-DELAY-2026-03 with no O2 or O3 details" and "no tool accepts booking_id"
- [ ] 6.2 Implement the deterministic answer validator (only the recommended option, `policy_ref` present, no personal data, no "booking changed" or "compensation approved" claims, consistent with `requires_human`), and verify tests for "a draft offering NB2450 is rejected" and "a valid draft about NB2412 is accepted"
- [ ] 6.3 Implement `answer_agent` with ADK (an `LlmAgent` with the facade functions as tools, no `output_schema`, a 5 s timeout, template fallback) and record each tool call, the validator result and `fallback_used` in the trace, and verify tests with a fake agent for "invalid draft → template sent", "timeout → template sent and the R5 human case is still created", plus an optional real-model integration test skipped without an API key
- [ ] 6.4 Wire the answer agent into `resolve_disruption` (it runs only when `question` is present; its output goes through the validator before `notify_passenger`), and verify a test where a request without a question never calls the agent and still sends the template

## 7. Integration and deliverables

- [ ] 7.1 Add end-to-end tests through the HTTP endpoint for the ABC123 base case and for the ambiguous query from design D11 (sent as `question` with a fake classifier → a single human case with R4 and R5, a message that promises nothing, and a trace naming both agents and the tools the answer agent called), and verify that `pytest` passes in full
- [ ] 7.2 Add the Engineering sections to the existing `README.md` (≤ 2 pages: problem, scope, assumptions, decisions and discarded alternatives, step classification table from design.md, risks, next steps, validation, and the new endpoint with a `curl` example), keeping its current run instructions, and verify that the documented `pytest`, `uvicorn` and `docker compose` commands run as written
- [ ] 7.3 Write `AI_USAGE.md` (≤ 1 page: AI tools used, outputs accepted, rejected or modified, how they were validated, decisions made personally, data never given to a model), and verify that it fits on one page and covers every required section

## Workflow follow-up

- Archive the change with `openspec archive resolve-passenger-disruption` after the team reviews the implementation.
