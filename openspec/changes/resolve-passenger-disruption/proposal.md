# Proposal

## Why

Passengers whose flight is modified call the contact center because they do not know what happened or what to do next. Nubara needs a first version that answers both questions from booking, operational and policy data. That data can be partial, stale or contradictory, and it must never leak unverified information or trigger high-impact actions (rebooking, compensation) without control.

## What Changes

- Add a backend service that, given a `booking_id`, resolves a disruption end to end: it reconciles operational events, decides whether the modification is relevant, evaluates the versioned policy, filters candidate options and returns a traceable decision.
- Resolve conflicting sources deterministically (source priority, degraded-source exclusion, recency) and escalate when trusted sources disagree.
- Detect missed connections derived from delays, not only direct delay thresholds.
- Filter out options that are expired, contradict policy, or cannot seat the whole booking party.
- Escalate to a human whenever a rule requires approval, data needed for the decision is missing, or a write has an indeterminate result.
- Never execute high-impact writes automatically: the service creates controlled requests or human cases, protected by idempotency keys.
- Accept an optional free-text question and classify it into a closed set of intents with an AI agent. The agent has no tools and only feeds flags to the deterministic pipeline; when it fails, a keyword classifier and a human take over.
- When a question is sent, let an AI agent compose the answer using only sanitized, read-only tools over the deterministic decision. Every draft is validated before it is sent, and the system falls back to a template.
- Build passenger-facing messages only from validated facts, each one tied to a `policy_ref`, with personal data minimized.
- Ship mocks that honour the tool contracts in the exam statement, plus automated tests for the key decisions of case `ABC123`.

## Capabilities

### New Capabilities

- `trip-disruption-assessment`: reconciles booking and operational data into a single verified view of what happened to the trip, including relevance and missed-connection detection.
- `disruption-entitlements`: evaluates versioned policy rules against the assessed trip, filters candidate options, and decides when a human must approve.
- `passenger-communication`: governs what may be shown or sent to the passenger and under which conditions a message may be delivered.
- `passenger-query-intake`: classifies an optional free-text question into validated intents and flags, with redaction, fallback and traceability.
- `passenger-answer-agent`: composes question-specific answers through sanitized read-only tools, with draft validation, template fallback and tool-call tracing.
- `controlled-actions`: governs high-impact writes (rebooking requests, human cases) with idempotency and safe handling of conflicts and indeterminate results.

### Modified Capabilities

None. This is the first version and there are no existing specs.

## Impact

- New Python 3.12 backend (one module per capability), exposed as a FastAPI service and packaged with Docker for local runs. There is no UI, no cloud deployment and no real airline system is touched.
- New mock adapters for `get_trip_context`, `get_operational_events`, `get_eligible_options`, `get_policy_rules`, `create_rebooking_request`, `create_human_case` and `notify_passenger`.
- New dependency: `google-adk`, used only by the intent classifier and the answer agent. It needs a model API key in `.env`, and it can be disabled with a setting.
- Deliverables: technical evidence (code and tests), an Engineering README of at most 2 pages, and an AI Usage & Decision Note of at most 1 page.
