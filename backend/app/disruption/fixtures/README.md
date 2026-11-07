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
