# Spec Delta

## Purpose

Builds a single, verified view of what happened to a passenger's trip from booking data and operational events that may be partial, stale or contradictory.

## ADDED Requirements

### Requirement: Source trust ordering
The system SHALL resolve conflicting operational events for the same segment using a fixed source priority (`OPS_CORE` > `AIRPORT_FEED` > `LEGACY_MIRROR`), using `recorded_at` recency as tie-breaker within the same source.

#### Scenario: Trusted delay wins over legacy on-time status
- **GIVEN** segment S1 has a `DELAY` of 160 minutes from `OPS_CORE` recorded at 10:48Z and a `STATUS: ON_TIME` from `LEGACY_MIRROR` recorded at 09:30Z
- **WHEN** the trip is assessed
- **THEN** S1 is assessed as delayed by 160 minutes with new departure 17:10
- **AND** event E-1012 is recorded as discarded, with the reason

### Requirement: Degraded sources excluded
The system SHALL exclude events from any source listed in `sources_degraded` when determining the trip status, and SHALL record each exclusion in the decision trace.

#### Scenario: Degraded source ignored
- **GIVEN** `_meta.sources_degraded` contains `LEGACY_MIRROR`
- **WHEN** the trip is assessed
- **THEN** no `LEGACY_MIRROR` event affects the assessed status
- **AND** the trace lists the excluded event ids

### Requirement: Stale events not trusted
The system SHALL treat an event as stale when its `recorded_at` is older than a configurable maximum age (default 2 hours) relative to the response's `_meta.retrieved_at`. Stale events SHALL NOT assert a segment status. A segment whose status depends only on stale events SHALL be marked `UNVERIFIED`, which requires human review.

#### Scenario: Fresh events are used
- **GIVEN** E-1001 was recorded at 10:48Z and the events were retrieved at 11:02:33Z
- **WHEN** the trip is assessed
- **THEN** E-1001 is considered fresh and is used

#### Scenario: Only stale information available
- **GIVEN** the only event for S1 is a `DELAY` recorded at 07:00Z and the events were retrieved at 11:02:33Z
- **WHEN** the trip is assessed
- **THEN** S1 is marked `UNVERIFIED`, the event is listed as stale in the trace, and human review is required

### Requirement: Unresolvable conflicts escalate
The system SHALL mark the assessment as `CONFLICTING` and require human review when two non-degraded sources of different priority report incompatible states for the same segment and recency does not settle it.

#### Scenario: Trusted sources disagree
- **GIVEN** `OPS_CORE` reports S1 as `CANCELLED` and `AIRPORT_FEED` reports S1 as `DELAYED`, both recent and non-degraded
- **WHEN** the trip is assessed
- **THEN** the assessment status is `CONFLICTING`
- **AND** no recommendation is produced automatically

### Requirement: Missed connection detection
The system SHALL compute each segment's estimated arrival as scheduled arrival plus delay, and SHALL flag a missed connection when the next segment departs before estimated arrival plus a configurable minimum connection time (default 60 minutes).

#### Scenario: Delay causes missed connection in LIM
- **GIVEN** S1 is scheduled to arrive at LIM at 17:55 and is delayed 160 minutes, and S2 departs LIM at 19:05 on the same date
- **WHEN** the trip is assessed
- **THEN** S1 estimated arrival is 20:35
- **AND** `missed_connection` is true for S2

### Requirement: Relevant modification
The system SHALL classify a modification as relevant only when it changes what the passenger must do or creates an entitlement (delay that triggers a rule, missed connection, cancellation, or gate change on a departing segment). Otherwise it SHALL classify it as informational.

#### Scenario: Delay below thresholds but connection missed
- **GIVEN** S1 is delayed 160 minutes and the connection to S2 is missed
- **WHEN** relevance is evaluated
- **THEN** the modification is relevant because of the missed connection

#### Scenario: Gate change only
- **GIVEN** the only event is a gate change on S1
- **WHEN** relevance is evaluated
- **THEN** the modification is informational and no entitlement is evaluated

### Requirement: Partial data handling
The system SHALL continue with the assessment when the booking context is `PARTIAL`, and SHALL record every missing field. It SHALL escalate only when a missing field is needed by the rule or option being applied.

#### Scenario: Missing change penalty does not block a no-fee rebooking
- **GIVEN** `fare_conditions.change_penalty_amount` is missing and the applicable entitlement is `REBOOK_NO_FEE`
- **WHEN** the decision is produced
- **THEN** the decision proceeds and lists `change_penalty_amount` as missing but not decision-relevant
