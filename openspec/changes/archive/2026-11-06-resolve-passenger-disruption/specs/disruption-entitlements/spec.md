# Spec Delta

## Purpose

Determines what the passenger is entitled to by evaluating the current versioned policy against the assessed trip, and selects which candidate options may be offered.

## ADDED Requirements

### Requirement: Current policy version only
The system SHALL evaluate only the policy version returned as current (for example `POL-DELAY-2026-03`) and SHALL never apply rules from `superseded_versions`. The decision SHALL carry that `policy_ref`, and every rule result SHALL carry the `rule_id` that produced it.

#### Scenario: Superseded policy ignored
- **GIVEN** the policy response has version `POL-DELAY-2026-03` and superseded version `POL-DELAY-2025-11`
- **WHEN** entitlements are evaluated
- **THEN** the decision's `policy_ref` is `POL-DELAY-2026-03`
- **AND** no rule of `POL-DELAY-2025-11` is evaluated

### Requirement: Deterministic rule evaluation
The system SHALL evaluate rule conditions deterministically against the assessed trip and SHALL list each rule as applied or not applied, with the reason.

#### Scenario: Case ABC123 entitlements
- **GIVEN** S1 is delayed 160 minutes, the S1→S2 connection is missed, and the booking includes a 7-year-old child
- **WHEN** entitlements are evaluated
- **THEN** R3 (`REBOOK_NO_FEE`) and R5 (`PRIORITY_HANDLING`) apply
- **AND** R1 is not applied because 160 < 180
- **AND** R2 is not applied because 160 < 240
- **AND** R4 is not applied because no compensation was requested

### Requirement: International flag from airport country
The system SHALL treat a segment as international when its origin and destination airports belong to different countries, using a fixed airport-to-country table. An airport missing from the table SHALL make the flag unknown and be recorded as decision-relevant missing data.

#### Scenario: Known airports
- **GIVEN** S1 flies SCL to LIM and is delayed 300 minutes
- **WHEN** entitlements are evaluated
- **THEN** the segment is international and R2 (`MEAL_VOUCHER`) applies

#### Scenario: Unknown airport
- **GIVEN** S1 departs from an airport that is not in the table and is delayed 300 minutes
- **WHEN** entitlements are evaluated
- **THEN** R2 is not applied and `airport_country:<code>` is listed as decision-relevant missing data
- **AND** `requires_human` is true with reason `MISSING_DECISION_DATA`

### Requirement: Expired options rejected
The system SHALL reject candidate options whose `retrieved_at + ttl_seconds` is earlier than the evaluation time, and SHALL re-fetch options instead of using expired ones.

#### Scenario: Options past TTL
- **GIVEN** options were retrieved at 11:02:35Z with `ttl_seconds` 120
- **WHEN** the evaluation time is 11:05:00Z
- **THEN** no option from that response is offered and options are re-fetched

### Requirement: Policy-inconsistent options rejected
The system SHALL reject any option whose terms contradict the applied entitlement, such as a non-zero `fare_difference` under `REBOOK_NO_FEE`, and SHALL record it as an inconsistency in the trace.

#### Scenario: Option charging a fee under a no-fee rule
- **GIVEN** option O2 has `fare_difference` 180000 CLP and the entitlement is `REBOOK_NO_FEE`
- **WHEN** options are filtered
- **THEN** O2 is rejected with reason `POLICY_INCONSISTENT`

### Requirement: Whole party must fit
The system SHALL reject rebooking options whose `seats_available` is lower than the number of passengers in the booking. Passengers travelling with a minor SHALL NOT be split across flights.

#### Scenario: Not enough seats for adult and child
- **GIVEN** the booking has 2 passengers and option O2 has 1 seat available
- **WHEN** options are filtered
- **THEN** O2 is rejected with reason `INSUFFICIENT_SEATS`

### Requirement: Low-confidence and unverified options not auto-offered
The system SHALL NOT auto-offer options with `LOW` confidence, or options whose policy was not retrieved and evaluated. It SHALL list them as alternatives that require agent review.

#### Scenario: Refund on a non-refundable fare
- **GIVEN** option O3 is a `REFUND` with confidence `LOW`, policy `POL-REFUND-2026-01` was not evaluated, and the fare is non-refundable
- **WHEN** options are filtered
- **THEN** O3 is not recommended and is marked `REQUIRES_AGENT_REVIEW`

### Requirement: Rejection reasons are complete
The system SHALL record every failing check for a rejected option, in the order TTL, seats, policy consistency, then confidence or evaluated policy. The first failing check SHALL be the primary reason.

#### Scenario: Option failing two checks
- **GIVEN** option O2 has 1 seat for 2 passengers and `fare_difference` 180000 CLP under `REBOOK_NO_FEE`
- **WHEN** options are filtered
- **THEN** O2 is rejected with reasons `INSUFFICIENT_SEATS` and `POLICY_INCONSISTENT`
- **AND** the primary reason is `INSUFFICIENT_SEATS`

### Requirement: Recommended option
The system SHALL recommend the valid option that satisfies the entitlement with no cost to the passenger, preferring `HIGH` confidence and then the earliest departure.

#### Scenario: Case ABC123 recommendation
- **GIVEN** O1 (NB2412, 2026-09-16 08:15, `fare_difference` 0, 4 seats, `HIGH`) is the only option left after filtering
- **WHEN** a recommendation is produced
- **THEN** O1 is recommended with `policy_ref` `POL-DELAY-2026-03`

### Requirement: Human approval gate
The system SHALL require human approval before any high-impact action when an applied rule has `requires_human_approval: true`, when the assessment is `CONFLICTING`, or when decision-relevant data is missing.

#### Scenario: Compensation requested
- **GIVEN** the request for ABC123 sets `compensation_requested` to true
- **WHEN** the decision is produced
- **THEN** R4 (`CASH_COMPENSATION`) applies and `human_reasons` contains both `R4_CASH_COMPENSATION` and `R5_PRIORITY_HANDLING`
- **AND** no compensation is executed automatically

#### Scenario: Minor in booking requires approval
- **GIVEN** R5 applies because the booking includes a minor
- **WHEN** the decision is produced
- **THEN** `requires_human` is true with reason `R5_PRIORITY_HANDLING`
- **AND** the recommendation is kept but the rebooking is not executed automatically
