# Spec Delta

## Purpose

Governs high-impact writes (rebooking requests and human escalations) so they are never executed without control, duplicated, or reported as done when the outcome is unknown.

## ADDED Requirements

### Requirement: No automatic execution of high-impact actions
The system SHALL NOT create a rebooking request automatically when the decision has `requires_human` true. In that case it SHALL create a human case with the recommendation as evidence.

#### Scenario: Case ABC123 escalates instead of rebooking
- **GIVEN** the decision recommends O1 and requires a human because of R5
- **WHEN** actions are executed
- **THEN** `create_human_case` is called and `create_rebooking_request` is not called

### Requirement: Deterministic idempotency key
The system SHALL derive the rebooking idempotency key deterministically from `booking_id`, `option_id` and `policy_ref`, so that retries of the same decision reuse the same key.

#### Scenario: Same decision yields same key
- **WHEN** the same decision is executed twice
- **THEN** both calls use the same idempotency key

### Requirement: Duplicate request handling
The system SHALL treat a `409 DUPLICATE_REQUEST` as an existing request, and SHALL reuse the returned `request_id` without creating a new one.

#### Scenario: Duplicate rebooking
- **WHEN** `create_rebooking_request` returns 409 with `request_id` "RBK-88231"
- **THEN** the result references "RBK-88231" with status `ALREADY_EXISTS`

### Requirement: Indeterminate result handling
The system SHALL retry a `503 UPSTREAM_TIMEOUT` at most once with the same idempotency key. If the result is still indeterminate it SHALL escalate to a human case and SHALL NOT tell the passenger that the booking was changed.

#### Scenario: Timeout twice
- **GIVEN** `create_rebooking_request` returns 503 on both attempts
- **WHEN** actions are executed
- **THEN** exactly two calls are made with the same key
- **AND** a human case is created with reason `REBOOKING_INDETERMINATE`
- **AND** the passenger message does not claim the rebooking succeeded

### Requirement: Pending confirmation is not completion
The system SHALL report a `201 PENDING_CONFIRMATION` rebooking as pending until `expires_at`, and SHALL NOT present it to the passenger as confirmed.

#### Scenario: Pending rebooking
- **WHEN** `create_rebooking_request` returns 201 with status `PENDING_CONFIRMATION`
- **THEN** the result is `PENDING` and includes `expires_at`

### Requirement: Human case evidence
The system SHALL include in each human case the reason code, the applied and rejected rules, the recommended and rejected options with reasons, discarded events, missing fields and booking identifiers. Personal identity documents SHALL be excluded.

#### Scenario: One case for several human reasons
- **GIVEN** the decision has `human_reasons` R4 and R5
- **WHEN** actions are executed
- **THEN** exactly one human case is created, and it lists both reasons

#### Scenario: Evidence for R5 escalation
- **WHEN** a human case is created for ABC123
- **THEN** the evidence contains R3, R5, O1 as recommended, O2 and O3 with their rejection reasons, and E-1012 as discarded
- **AND** it does not contain `document_id`
