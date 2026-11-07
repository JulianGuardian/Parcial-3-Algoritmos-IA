# Tasks

## 1. Backend response fields

- [x] 1.1 Add `segments` and `human_reasons` to `AgentResponse`, built by `build_response` from the turn's evaluation, and verify tests for the ABC123 values and for "no personal data or source names in the response"

## 2. API access

- [x] 2.1 Add the `/api` proxy to `vite.config.ts` (`API_PROXY_TARGET`, default `http://localhost:8000`) and set it to `http://backend:8000` in `docker-compose.yml` (frontend `depends_on` backend, `VITE_DEMO_NOW` pinned), and verify that `curl localhost:5173/api/v1/conversations` reaches the backend under compose
- [x] 2.2 Add `src/api/` with the TypeScript `AgentResponse` types, `startConversation`, `sendMessage` (optional `confirm_option_id`, and `now` from `VITE_DEMO_NOW`), a typed `ApiError`, and the mapper to the card view, and verify Vitest tests with a mocked `fetch` (request bodies, error parsing, mapping of ABC123)

## 3. Chat wiring

- [x] 3.1 Add the booking step and the conversation state in `App` (start, send, in-flight, error banner, 404 recovery), and stop seeding the sample conversation, and verify Vitest tests for "start ABC123 → composer enabled", "unknown booking → message", and "CONVERSATION_NOT_FOUND → back to booking"
- [x] 3.2 Add the confirm action to `DecisionCard` (shown only for `CONFIRM_OPTION`, sends `confirm_option_id`) and a next-step line for every `next_step`, and verify Vitest tests for "button only for CONFIRM_OPTION" and "pressing it sends O1"

## 4. Verification and docs

- [x] 4.1 Run the frontend tests, lint and build, plus the backend tests, and verify end to end with `docker compose up` that ABC123 shows the card and DEF456 can be confirmed into `REBOOKING_PENDING`
- [x] 4.2 Document the connected chat in `README.md` (booking codes to try, `VITE_DEMO_NOW`, `API_PROXY_TARGET`), and verify that the commands run as written
