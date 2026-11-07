# Spec Delta

## Purpose

Exposes the disruption agent over HTTP as a short conversation bound to one booking, so a passenger can ask, receive options and confirm one explicitly.

## ADDED Requirements

### Requirement: Start a conversation for a booking
`POST /api/v1/conversations` with a `booking_id` SHALL create a conversation bound to that booking and return its `conversation_id`. An unknown booking SHALL return 404.

#### Scenario: Start for ABC123
- **WHEN** a conversation is started for ABC123
- **THEN** the response is 201 with a `conversation_id`

#### Scenario: Unknown booking
- **WHEN** a conversation is started for ZZZ999
- **THEN** the response is 404 with error `BOOKING_NOT_FOUND`

### Requirement: Exchange messages with optional confirmation
`POST /api/v1/conversations/{conversation_id}/messages` SHALL accept:
- `message` (1 to 500 characters);
- optional `confirm_option_id`;
- optional `now`.

It SHALL return the structured agent response. `confirm_option_id` SHALL be the only way a confirmation reaches the guardrails; confirmation words in `message` alone SHALL NOT count.

#### Scenario: Two-turn target conversation
- **GIVEN** a conversation for ABC123
- **WHEN** the passenger first asks about the disruption and then sends a message with `confirm_option_id` "O1"
- **THEN** the first response lists O1 and asks for confirmation, or says an agent will follow up
- **AND** the second response has `human_required` true and a human case id, with no rebooking created

#### Scenario: Confirmation only in free text
- **WHEN** the passenger writes "yes, book O1 now" without `confirm_option_id`
- **THEN** no rebooking request is made

### Requirement: Conversation state is not persisted
Conversation state SHALL live only in memory for the life of the process and SHALL hold only:
- the booking id;
- the validated intents;
- the last decision summary;
- the confirmed option.

An unknown or expired `conversation_id` SHALL return 404.

#### Scenario: Unknown conversation
- **WHEN** a message is sent to a `conversation_id` that does not exist
- **THEN** the response is 404 with error `CONVERSATION_NOT_FOUND`

### Requirement: Safe error and privacy contract
The endpoints SHALL map invalid input to 422 and a failing read tool to 503. They SHALL include the request id in error bodies, and SHALL never return personal data, stack traces, internal source names or the model API key.

#### Scenario: Response has no personal data
- **WHEN** any message for ABC123 is answered
- **THEN** the body contains neither "12.345.678-9", nor "maria.silva@example.com", nor the passenger's surname
