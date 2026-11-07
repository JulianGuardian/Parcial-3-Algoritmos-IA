# Spec Delta

## Purpose

Controls what the passenger may see or receive about a disruption, ensuring messages contain only validated, policy-backed facts and minimal personal data.

## ADDED Requirements

### Requirement: Passenger-visible content
The system SHALL include in passenger output only: what happened to their segments, the relevant consequence (for example a missed connection), the valid recommended option, their entitlements, the `policy_ref`, and whether a person will follow up.

#### Scenario: Case ABC123 message content
- **GIVEN** the decision for ABC123 recommends O1 under R3 and requires human follow-up for R5
- **WHEN** the passenger message is built
- **THEN** it states the 160-minute delay, the missed connection to NB2410, O1 as the proposed option, and that an agent will confirm it
- **AND** it includes `policy_ref` `POL-DELAY-2026-03`

### Requirement: Internal and unverified data withheld
The system SHALL NOT expose internal source names, option confidence levels, discarded or degraded events, superseded policy versions, rejected options, or any fact that did not pass validation.

#### Scenario: Legacy on-time status not shown
- **GIVEN** event E-1012 (`ON_TIME`) was discarded
- **WHEN** the passenger message is built
- **THEN** the message does not mention an on-time status or `LEGACY_MIRROR`

### Requirement: Personal data minimization
The system SHALL NOT include `document_id`, full email or full phone number in passenger messages, logs, API responses or any payload sent to an AI agent. Co-travellers in the same booking MAY be referenced by first name only.

#### Scenario: No identity document in outputs
- **GIVEN** passenger P1 has `document_id` "12.345.678-9"
- **WHEN** the decision, the message and the logs are produced
- **THEN** none of them contains "12.345.678-9"

### Requirement: Policy reference mandatory
The system SHALL NOT send a passenger notification that lacks a `policy_ref`, and SHALL treat a `422 UNVALIDATED_CONTENT` response as a validation failure that blocks delivery and is recorded.

#### Scenario: Notification rejected for missing policy reference
- **WHEN** `notify_passenger` returns 422 with detail `missing policy_ref`
- **THEN** the message is not retried unchanged and the failure is recorded in the trace

### Requirement: Automatic delivery conditions
The system SHALL deliver a recommendation automatically only when all of these hold: the assessment is not `CONFLICTING`, no applied rule requires human approval, the option is valid and unexpired, and a `policy_ref` is present. Otherwise it SHALL send only an informational message saying that an agent will follow up.

#### Scenario: Compensation neither promised nor denied
- **GIVEN** `compensation_requested` is true and R4 requires human approval
- **WHEN** the notification is prepared
- **THEN** the message says that an agent will review the compensation request
- **AND** it states no amount and does not promise or deny compensation

#### Scenario: Human approval required
- **GIVEN** R5 requires human approval
- **WHEN** the notification is prepared
- **THEN** the message explains what happened and that an agent will confirm the proposed option
- **AND** it does not state that the booking was changed
