# Proposal

## Why

The passenger chat UI (`add-passenger-chat-ui`) still runs on sample data, and the conversational agent API (`build-disruption-agent`) has no client. Without the connection, a passenger cannot start a conversation, receive the agent's structured answer, or confirm a rebooking option. That last step is the only path the guardrails accept for a rebooking.

## What Changes

- **Frontend:**
  - asks for the booking code and starts a conversation through `POST /api/v1/conversations`;
  - sends every message through `POST /api/v1/conversations/{id}/messages`;
  - renders the `AgentResponse` (reply text and trip-update card).
- **Confirmation:** a "Confirm this option" button appears only when `next_step` is `CONFIRM_OPTION`. It sends `confirm_option_id`, the structured confirmation the guardrails require.
- **Connection:** the Vite dev server proxies `/api` to the backend, both locally and in Docker compose, so the browser never makes a cross-origin call and the backend needs no CORS.
- **Backend:** `AgentResponse` gains two passenger-safe fields that the card already renders: `segments` (verified status per segment) and `human_reasons` (reason codes, which the UI maps to plain language).
- **Errors:** an expired or unknown conversation (`404 CONVERSATION_NOT_FOUND`) sends the passenger back to the booking step with a message. Other errors show a banner and keep the typed text.
- **Demo time:** the evaluation time can be pinned with `VITE_DEMO_NOW`, because the statement's options expire at 2026-09-15T11:04:35Z.

## Capabilities

### New Capabilities

- `chat-agent-integration`: how the chat UI drives the conversational agent API. It covers starting a conversation, sending messages, structured confirmation, response rendering, error recovery and the same-origin proxy, plus the two response fields the UI relies on.

### Modified Capabilities

None. The response fields are additive and specified from the client's side.

## Impact

- **Frontend:** a new `src/api/` client, changes to the chat state in `App.tsx`, a booking step, a confirm action on `DecisionCard`, and the proxy in `vite.config.ts`. The sample conversation is no longer seeded at start.
- **Backend:** `agents/contracts.py` and `agents/response.py` gain the two additive fields.
- **`docker-compose.yml`:** the frontend proxies to the `backend` service and pins `VITE_DEMO_NOW`.
- **README:** a short section on how to use the connected chat.
