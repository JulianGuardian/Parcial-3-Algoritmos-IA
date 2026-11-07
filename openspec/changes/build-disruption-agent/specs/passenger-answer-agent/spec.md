# Spec Delta

## REMOVED Requirements

### Requirement: Sanitized read-only tools
**Reason**: Part B requires the agent to choose its tools through function calling and to create rebookings and human cases itself, so the agent can no longer be strictly read-only.
**Migration**: The read tools stay sanitized under `disruption-agent` ("Least-privilege tool set", "Tool results are data, not instructions"), and the new write tools are guarded by `agent-tool-guardrails`.
