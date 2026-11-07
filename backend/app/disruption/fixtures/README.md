# Fixtures

Sample tool responses transcribed from the exam statement (section 2, "Available systems"). The mocks must return these shapes unchanged.

| File | Tool | Type |
|---|---|---|
| `get_trip_context_ABC123.json` | `get_trip_context("ABC123")` | Read |
| `get_operational_events_S1_S2.json` | `get_operational_events(["S1","S2"])` | Read |
| `get_eligible_options_ABC123.json` | `get_eligible_options(trip_context)` | Read |
| `get_policy_rules_DELAY.json` | `get_policy_rules("DELAY")` | Read |
| `create_rebooking_request.json` | `create_rebooking_request(option, idempotency_key)` | Write |
| `create_human_case.json` | `create_human_case(reason, evidence)` | Write |
| `notify_passenger.json` | `notify_passenger(message)` | Write |

The write-tool files are keyed by HTTP status code. Per the statement, a `503` from `create_rebooking_request` means the actual result is **indeterminate**: the request may or may not have been created.

All personal data in `get_trip_context_ABC123.json` is fictitious sample data from the statement.

## Evaluation fixtures

These are not part of the statement. They were added for the agent evaluation cases (change `build-disruption-agent`, task 1.1), and all their personal data is fictitious.

| File | Purpose |
|---|---|
| `get_trip_context_DEF456.json` | Same flights as ABC123 with a single adult: R5 does not apply, so a confirmed O1 can be rebooked (failed-write case). |
| `get_trip_context_GHI789.json` | Same route on segments `G1` and `G2`. |
| `get_operational_events_G1_G2.json` | `OPS_CORE` reports G1 `CANCELLED` and `AIRPORT_FEED` reports it `DELAYED`, giving trusted sources that contradict each other (contradictory-sources case). |

DEF456 and GHI789 reuse `get_eligible_options_ABC123.json` and the S1/S2 events as needed.
