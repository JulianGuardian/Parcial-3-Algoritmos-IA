# AI Usage & Decision Note

## AI tools used

| Tool | What for |
|---|---|
| Claude Code (Claude Opus 5.5) | Reading the exam statement from photos; resolving the ambiguities; drafting the OpenSpec change (proposal, specs, design, tasks); transcribing the sample responses into fixtures; implementing and testing tasks 5.1–5.5 (actions, passenger message, pipeline, endpoint). |
| OpenSpec CLI 1.16 (not a model) | Spec-driven structure, `openspec validate --strict` and task tracking. |
| _TODO: tools used for the core (2.x–3.x) and the ADK agents (4.x, 6.x)_ | |

In the product, AI appears only at the two ends of the flow (design D11–D13). An ADK `intent_classifier` turns the question into a closed set of intents. An ADK `answer_agent` words the reply using read-only, sanitized tools. Every decision in between is deterministic.

## Outputs accepted, modified or rejected

- **Accepted, after checking by hand against the statement:**
  - the reading of ABC123: a missed connection gives R3; R1 and R2 do not apply at 160 min; R5 requires a human; O2 fails on seats and fee; E-1012 is discarded;
  - the proposed resolutions of the section 4 ambiguities;
  - the idempotency and 503 strategy.
- **Modified:**
  - the stack, from plain Python 3.11 to the Python 3.12 + FastAPI + Docker that we chose;
  - the layout, from a new `src/` package to our existing `backend/`;
  - the artifacts, rewritten in English;
  - the answer agent, which was first proposed without tools and now gets read-only tools over a sanitized facade.
- **Rejected:**
  - an agent with direct access to the exam tools or to any write tool;
  - team and ownership details inside spec files;
  - dropping docker-compose, which we already use.

## How we validated them

- Every spec scenario is backed by a test (`pytest`: 120 passing as of PR #5). Tests also assert that no personal data appears in responses, messages or human-case evidence.
- `openspec validate --all --strict` passes on every change.
- Every diff is reviewed manually before commit, and every PR is reviewed by another team member.
- _TODO: confirm that the fixtures were checked line by line against the exam photos._

## Decisions we made personally

- The stack (Python 3.12, FastAPI, Docker) and building on the existing backend skeleton.
- Using AI now, through Google ADK, so we can show which agent acted and which tools it called; keeping escalation and all writes deterministic.
- Giving the answer agent tools, limited to read-only sanitized views scoped to one booking.
- Removing the unused `.claude/` folder, and splitting the work among three people.
- _TODO: each member adds their own decisions._

## Information we would never give to a model

- Identity documents, full emails, phone numbers or surnames of passengers.
- Raw tool responses (unreconciled events, rejected options, superseded policies) given to the runtime agents.
- Write tools: rebooking, compensation, notifications or human cases.
- API keys, `.env` files or any credential.
- Real customer data in prompts during development; only the exam's fictitious samples were used.
