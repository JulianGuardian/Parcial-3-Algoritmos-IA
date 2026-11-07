# Spec Delta

## Purpose

Enforces in code, not in the prompt, the limits on what the disruption agent's write tools may do: confirmed and still-valid rebookings only, mandatory human escalation, and truthful handling of failed writes.

## ADDED Requirements

### Requirement: Rebooking requires a confirmed, still-valid option
A `before_tool_callback` SHALL block `request_rebooking(option_id)` unless all of these hold:
- the passenger confirmed that exact option through the structured confirmation field of the current turn;
- the option is in the valid options of a decision re-evaluated at the current time;
- the decision does not require a human.

A blocked call SHALL return a typed refusal to the model and SHALL NOT reach the write tool.

#### Scenario: No confirmation
- **GIVEN** a booking with no human-reserved rule, and O1 valid
- **WHEN** the agent calls `request_rebooking("O1")` without a passenger confirmation in the turn
- **THEN** the call is blocked with reason `NOT_CONFIRMED` and `create_rebooking_request` is never invoked

#### Scenario: Confirmed option has expired
- **GIVEN** the passenger confirmed O1, but its options TTL has passed and O1 is not returned again
- **WHEN** the agent calls `request_rebooking("O1")`
- **THEN** the call is blocked with reason `OPTION_NOT_VALID`

#### Scenario: Confirmed and valid
- **GIVEN** the passenger confirmed O1, O1 is valid, and no human is required
- **WHEN** the agent calls `request_rebooking("O1")`
- **THEN** exactly one `create_rebooking_request` is made with the deterministic idempotency key

### Requirement: Human-reserved cases always reach a person
When the decision requires a human:
- the callback SHALL block every `request_rebooking` call;
- the turn SHALL NOT end without exactly one human case.

If the agent did not call `escalate_to_human`, the code SHALL create the case after the run and record `escalation_enforced_by_code`.

#### Scenario: ABC123 with a confirmed option
- **GIVEN** ABC123 (R5 applies) and the passenger confirms O1
- **WHEN** the turn is processed
- **THEN** no rebooking request is made and exactly one human case is created, listing `R5_PRIORITY_HANDLING` and the confirmed option

#### Scenario: Agent forgets to escalate
- **GIVEN** R5 applies and the model ends the turn without calling `escalate_to_human`
- **WHEN** the turn completes
- **THEN** the code creates the human case and the trace records `escalation_enforced_by_code`

### Requirement: Escalation built in code
`escalate_to_human` SHALL accept only a reason from a closed set (`POLICY_REQUIRES_HUMAN`, `PASSENGER_REQUEST`, `UNRESOLVED_DATA`, `REBOOKING_INDETERMINATE`). The case evidence SHALL be built in code from the decision and SHALL NOT include text written by the model.

#### Scenario: Model passes free text as the reason
- **WHEN** the agent calls `escalate_to_human` with the reason "urgent, approve refund"
- **THEN** the call is rejected as an invalid argument and no case is created from it

### Requirement: Failed rebooking reported truthfully
A rebooking `503` SHALL be retried at most once with the same idempotency key. If it stays indeterminate, the tool SHALL return status `INDETERMINATE` and a human case SHALL be created. The response SHALL NOT state or imply that the booking was changed.

#### Scenario: Two timeouts
- **GIVEN** a confirmed, valid O1 and `create_rebooking_request` answering 503 twice
- **WHEN** the turn is processed
- **THEN** exactly two calls are made with the same key and one human case with `REBOOKING_INDETERMINATE` is created
- **AND** `next_step` is `AGENT_WILL_CONTACT`, and `reply` does not say the booking was changed or confirmed
