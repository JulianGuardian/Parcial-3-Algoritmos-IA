# Design

## Context

- **Frontend:** `frontend/`, built with React 19, MUI and Vite. It has a chat page, a composer and a `DecisionCard`, and it renders sample data shaped like the `/resolve` response.
- **Backend:** `/api/v1/conversations` is backed by `disruption_companion`; each turn returns an `AgentResponse`.
- **Docker compose:** runs both services, on ports 8000 and 5173.
- **Model:** without `GOOGLE_API_KEY`, each turn degrades to the deterministic path, so the UI must work in both modes.

## Goals / Non-Goals

**Goals:** a working end-to-end chat for the evaluation bookings (ABC123, DEF456 and GHI789), structured confirmation, and clear error recovery.

**Non-Goals:** no authentication, persistent history, streaming, production build or deployment.

## Decisions

### D1. Vite proxy instead of CORS
The browser calls the relative path `/api/...`. `vite.config.ts` proxies it to `API_PROXY_TARGET`: `http://localhost:8000` locally, `http://backend:8000` in compose.

*Alternative:* CORS on the backend (rejected because it needs one more setting and an allow-list, and the dev proxy already solves it for the only deployment there is).

### D2. Map `AgentResponse` to the existing card view
`src/api/` mirrors `AgentResponse`, and a small mapper turns it into the card's view model. `DecisionCard` keeps its sections, and its tests keep covering the rendering. The card gains an optional `onConfirm`, which is shown only when `next_step` is `CONFIRM_OPTION`, and it now renders a next-step line for every `next_step`.

*Alternative:* rewrite the card around `AgentResponse` (rejected because it duplicates work and loses the existing tests).

### D3. Two additive backend fields
`AgentResponse.segments` reuses `SegmentView`, which `get_trip_status` already returns. `AgentResponse.human_reasons` copies the decision's codes. Both come from the evaluation that `build_response` already computes, so they cannot disagree with the other fields.

### D4. Conversation state lives in `App`
`App` keeps four things:
- `bookingId`;
- `conversationId`;
- the messages;
- the in-flight and error flags.

**Booking step.** When there is no conversation, a booking step replaces the composer.

**Confirming.** A confirmation is sent as a user message ("I confirm flight NB2412 on 2026-09-16"), with `confirm_option_id` attached.

**Recovery.** A `404 CONVERSATION_NOT_FOUND` clears the conversation id and the messages.

### D5. Pinned demo time
The statement's options expire at 2026-09-15T11:04:35Z. `VITE_DEMO_NOW`, if set, is sent as `now` on every message. Compose sets it to `2026-09-15T11:03:00Z`, and without it the backend uses the real clock.

## Risks / Trade-offs

- [A real model takes 2–6 s per turn] → the composer shows the in-flight state and disables sending.
- [Pinning `now` in compose hides the real-clock behaviour] → this is documented, and unsetting the variable restores it.
- [The proxy exists only in the dev server] → acceptable, because there is no production frontend build in scope.
