# passenger-answer-agent Specification

## Purpose
Lets an AI agent compose a passenger answer tailored to their question, using only sanitized read-only views of the deterministic decision, with every draft validated before it can be sent.

## Requirements

### Requirement: Sanitized read-only tools
The answer agent SHALL access trip and decision data only through read-only tools that return already-reconciled, sanitized results: trip summary, entitlements and current policy rules. It SHALL NOT have access to the raw source tools or to any write tool.

#### Scenario: Agent cannot see discarded data
- **WHEN** the agent calls the trip summary tool for ABC123
- **THEN** the result shows S1 delayed 160 minutes with a missed connection
- **AND** it contains neither event E-1012, nor `LEGACY_MIRROR`, nor `document_id`, email or phone

#### Scenario: Agent cannot see rejected options
- **WHEN** the agent calls the entitlements tool for ABC123
- **THEN** the result contains O1 as the recommended option, R3 and R5, and `POL-DELAY-2026-03`
- **AND** it contains no details of O2 or O3

### Requirement: Tools scoped to the current request
The agent's tools SHALL be bound to the booking being resolved and SHALL NOT accept a booking identifier, so that the agent cannot read any other booking.

#### Scenario: No booking parameter
- **WHEN** the tool definitions given to the agent are inspected
- **THEN** none of them accepts a `booking_id` or a passenger identifier

### Requirement: Draft validated before sending
The system SHALL reject the agent's draft and send the template answer instead when the draft mentions an option or flight other than the recommended one, omits the `policy_ref`, contains personal data, claims that the booking was changed or compensation approved, or contradicts `requires_human`.

#### Scenario: Draft offers a rejected option
- **GIVEN** the agent's draft says "you can take NB2450 tonight"
- **WHEN** the draft is validated
- **THEN** it is rejected and the template answer is sent, and the trace records the validation failure

#### Scenario: Valid draft
- **GIVEN** the draft mentions only NB2412 on 2026-09-16, includes `POL-DELAY-2026-03`, and says an agent will confirm
- **WHEN** the draft is validated
- **THEN** it is accepted and passed to the notification step

### Requirement: Escalation stays deterministic
The agent SHALL NOT decide whether a human is involved. Human cases SHALL be created by the deterministic pipeline whether or not the agent runs or succeeds.

#### Scenario: Agent fails
- **GIVEN** the answer agent times out
- **WHEN** ABC123 is resolved with a question
- **THEN** the human case for R5 is still created and the template answer is sent

### Requirement: Agent tool-call traceability
The system SHALL record in the decision trace every tool the agent called, its latency, the validator result and whether the template fallback was used.

#### Scenario: Trace lists tool calls
- **WHEN** the agent answers using the trip summary and entitlements tools
- **THEN** the trace lists both calls, under `agent: answer_agent`, with their latencies and the validator result
