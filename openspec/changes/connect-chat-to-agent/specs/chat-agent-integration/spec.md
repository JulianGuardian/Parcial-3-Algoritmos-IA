# Spec Delta

## Purpose

Connects the passenger chat UI to the conversational disruption agent, so a passenger can ask about their booking, see the verified answer and confirm a rebooking option through a structured action.

## ADDED Requirements

### Requirement: Conversation starts from a booking code
The chat SHALL ask for a booking code before the first message, and SHALL start a conversation through `POST /api/v1/conversations`. Messages SHALL be sent only after a `conversation_id` was obtained.

#### Scenario: Start for ABC123
- **WHEN** the passenger enters "ABC123" and starts
- **THEN** the UI calls `POST /api/v1/conversations` with `{"booking_id": "ABC123"}` and enables the composer

#### Scenario: Unknown booking
- **WHEN** the API answers 404 `BOOKING_NOT_FOUND`
- **THEN** the UI shows "We could not find that booking" and stays on the booking step

### Requirement: Messages render the agent response
Each passenger message SHALL be sent through `POST /api/v1/conversations/{id}/messages`. The assistant turn SHALL show `reply` as plain text and a trip-update card built from `segments`, `entitlements`, `options`, `human_required`, `human_reasons`, `policy_refs`, `human_case_id` and `next_step`. Fields the passenger must not see (`trajectory`, `reply_fallback`, rule ids) SHALL NOT be rendered.

#### Scenario: ABC123 answer
- **WHEN** the agent answers the first ABC123 message
- **THEN** the card shows NB500 delayed 160 min, the missed NB2410 connection, the free rebooking, option NB2412, that an agent will confirm, and `POL-DELAY-2026-03`

### Requirement: Confirmation is a structured action
A "Confirm this option" button SHALL appear only when `next_step` is `CONFIRM_OPTION`. Pressing it SHALL send a message whose `confirm_option_id` is the option's id. Typed text SHALL NOT be sent as a confirmation.

#### Scenario: Confirm O1 for DEF456
- **GIVEN** the answer for DEF456 has `next_step` `CONFIRM_OPTION` and option O1
- **WHEN** the passenger presses "Confirm this option"
- **THEN** the UI sends `confirm_option_id: "O1"` and renders the next answer, for example `REBOOKING_PENDING`

#### Scenario: No button when a human must decide
- **WHEN** the answer has `human_required` true and `next_step` `AGENT_WILL_CONTACT`
- **THEN** no confirm button is shown

### Requirement: Error recovery
On `404 CONVERSATION_NOT_FOUND`, the UI SHALL return to the booking step with a message. On any other error, it SHALL show an error banner, keep the passenger's typed text, and allow resending.

#### Scenario: Backend restarted
- **WHEN** a message gets 404 `CONVERSATION_NOT_FOUND`
- **THEN** the UI says the conversation expired and asks for the booking code again

#### Scenario: Agent unavailable
- **WHEN** a message gets 503
- **THEN** an error banner is shown and the typed text is kept

### Requirement: Same-origin API access
The browser SHALL call the API on its own origin under `/api`, and the dev server SHALL proxy those calls to the backend (`API_PROXY_TARGET`, default `http://localhost:8000`). No cross-origin request SHALL be needed.

#### Scenario: Docker compose
- **WHEN** both services run with `docker compose up`
- **THEN** `http://localhost:5173/api/v1/conversations` reaches the backend service

### Requirement: Response carries passenger-safe card data
Every `AgentResponse` SHALL include:
- `segments`: per segment, the flight number, airports, verified status, delay, estimated times and missed-connection flag;
- `human_reasons`: reason codes.

Both SHALL be built in code from the same evaluation as the other fields, and SHALL contain no personal data or source names.

#### Scenario: Segments for ABC123
- **WHEN** an ABC123 turn is answered
- **THEN** `segments` lists S1 `DELAYED` 160 with estimated departure `2026-09-15T17:10`, and S2 with `missed_connection` true
- **AND** `human_reasons` contains `R5_PRIORITY_HANDLING`
