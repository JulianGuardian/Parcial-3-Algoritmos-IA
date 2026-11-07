# Spec Delta

## Purpose

Defines the card that summarizes a disruption decision for the passenger: what happened to their flights, what they are entitled to, the proposed option and the next step, showing only passenger-visible content.

## ADDED Requirements

### Requirement: Card sections
The decision card SHALL be titled "Your trip update" and SHALL show these sections when they have content: "What happened", "Your benefits", "Proposed option" and "Next step". A section without content SHALL be omitted.

#### Scenario: Full decision
- **WHEN** a decision has flight changes, an entitlement, a recommended option and a human follow-up
- **THEN** the card shows the four sections in that order under the title

#### Scenario: Decision without a recommended option
- **WHEN** a decision has no recommended option
- **THEN** the "Proposed option" section is not shown

### Requirement: Flight status
For each flight the card SHALL show the flight number, the route and a status in words: "On schedule", "Delayed", "Cancelled" or "Being confirmed". A delayed flight SHALL also show the delay in minutes and the new estimated departure time.

#### Scenario: Delayed flight
- **WHEN** flight NB500 from SCL to LIM is delayed 160 minutes with estimated departure 17:10
- **THEN** the card shows "NB500", "SCL → LIM", "Delayed", "160 min" and "17:10"

#### Scenario: Status shown without color alone
- **WHEN** a flight status is displayed in any palette
- **THEN** the status text is visible and not conveyed only by color

### Requirement: Unverified status is not detailed
When the status of a flight is unverified or in conflict, the card SHALL show "Being confirmed" for that flight and SHALL NOT show a delay or an estimated time for it.

#### Scenario: Conflicting sources
- **WHEN** a flight has the status CONFLICTING or UNVERIFIED
- **THEN** the card shows "Being confirmed" for it and no delay minutes or estimated times

### Requirement: Missed connection notice
When a flight is marked as a missed connection, the card SHALL show a notice naming that flight and saying the connection will be missed.

#### Scenario: Connection will be missed
- **WHEN** flight NB2410 from LIM to MEX is marked as a missed connection
- **THEN** the card shows a notice that the connection NB2410 will be missed

### Requirement: Benefits in plain words
The card SHALL list each applied entitlement with a plain-language label: "Free rebooking", "Meal voucher", "Priority handling" and "Compensation request: an agent will review it". An entitlement without a known label SHALL be shown as "Additional benefit: an agent will give you details", never as its internal code.

#### Scenario: Known entitlements
- **WHEN** the applied entitlements are REBOOK_NO_FEE and PRIORITY_HANDLING
- **THEN** the card lists "Free rebooking" and "Priority handling"

#### Scenario: Unknown entitlement
- **WHEN** an entitlement code has no label
- **THEN** the card shows the generic additional-benefit text and not the code

### Requirement: Compensation is neither promised nor quantified
The card SHALL NOT show an amount of compensation and SHALL NOT state that compensation was approved or denied.

#### Scenario: Compensation entitlement
- **WHEN** the decision includes CASH_COMPENSATION
- **THEN** the card says an agent will review the request and shows no amount

### Requirement: Proposed option
The card SHALL show the recommended option with flight number, route, date and departure time, and SHALL add "No extra cost" when its fare difference is zero. It SHALL NOT state that the booking was changed.

#### Scenario: Recommended rebooking
- **WHEN** the recommended option is NB2412 from LIM to MEX on 2026-09-16 at 08:15 with fare difference 0
- **THEN** the card shows that flight, route, date and time with "No extra cost"
- **AND** it does not say the booking was changed

### Requirement: Next step
When the decision requires a human, the "Next step" section SHALL say that an agent will review and confirm before any change is made, and SHALL list each reason in plain words, never as an internal code.

#### Scenario: Minor in the booking
- **WHEN** the decision requires a human because the booking includes a minor
- **THEN** the card says an agent will confirm before any change is made and mentions priority handling for travellers with a minor

#### Scenario: Reason without a label
- **WHEN** a human reason has no label
- **THEN** the card shows a generic review reason and not the code

### Requirement: References
The card SHALL show the policy reference and, when there is one, the case reference, in a monospace font.

#### Scenario: References present
- **WHEN** the decision has policy reference POL-DELAY-2026-03 and case reference HC-1
- **THEN** both are shown in monospace under labels "Policy reference" and "Case reference"

### Requirement: Internal data is never shown
The card SHALL NOT show source names, option confidence, discarded or degraded events, rejected options, rule identifiers, superseded policy versions, trace entries, or personal data other than first names.

#### Scenario: Card for the sample booking
- **WHEN** the card for the sample booking is rendered
- **THEN** its text contains none of "LEGACY_MIRROR", "OPS_CORE", "R3", "R5" or an identity document number
