# Spec Delta

## ADDED Requirements

### Requirement: Rebooking only for a confirmed option
The system SHALL request a rebooking only for an option the passenger explicitly confirmed and that is still valid at the time of the request. No path, deterministic or agentic, SHALL create a rebooking request from a recommendation alone.

#### Scenario: Recommendation without confirmation
- **GIVEN** an adult-only booking where O1 is valid and no human is required
- **WHEN** the disruption is resolved without a confirmed option
- **THEN** no `create_rebooking_request` call is made, and `next_step` asks the passenger to confirm O1
