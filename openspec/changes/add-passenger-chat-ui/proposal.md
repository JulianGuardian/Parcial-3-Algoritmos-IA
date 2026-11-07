# Proposal

## Why

The repository only has a backend. Passengers whose flight changed have no screen where they can read what happened and what to do next, which is the goal of the disruption feature. Cubik IA (`C:\dev\Cubik-IA\frontend`) already solved the same screen problem with a reviewed design: a Vite + React + MUI chat page with a light/dark theme, built first as a pure UI over example data and verified with tests. This change brings that design over, adapted to Nubara: all math features are dropped and the "step-by-step resolution" card becomes a card that explains the disruption decision.

## What Changes

- Add a `frontend/` package (React, TypeScript, Vite, pnpm) with the standard `src` folder layout, lint, build and test scripts.
- Add the visual foundation: MUI with a light/dark theme that follows the system preference, and self-hosted fonts (no third-party font request).
- Add the chat page as a feature module made of four parts: error banner, a bordered container, the messages area and the composer.
- Messages area: loading text, empty-conversation welcome from the Nubara assistant, and user and assistant bubbles.
- **Decision card** under assistant messages: what happened to each flight, the entitlements, the proposed option at no extra cost, whether an agent will follow up, the case reference and the `policy_ref`. It shows only what the passenger is allowed to see (spec `passenger-communication`).
- Composer: multiline input limited to 500 characters (the backend limit), send button, and suggested-question chips that fill the input.
- The page is driven by local state and example data shaped like the real `POST /api/v1/disruptions/{booking_id}/resolve` response. It makes no API calls.
- User-facing text is in English, like the backend messages and the README.
- Not ported from Cubik: the calculator keyboard, the live math preview, KaTeX rendering, the plain-text math heuristics, the resolution card and the 180-character rule.

**Out of scope (separate later changes):** connecting to the backend (client, Vite proxy or CORS, booking id entry, 404 and 503 handling), routing, authentication, a theme toggle, history, running the frontend in Docker Compose, and translating the backend messages.

## Capabilities

### New Capabilities
- `frontend-app-shell`: the runnable frontend package: development server, production build, quality scripts and the chat page as root page.
- `frontend-src-layout`: the folder structure of the frontend `src` and what each folder is for.
- `app-theme`: light and dark visual theme that follows the system, typography and surface styling.
- `chat-page`: page layout, screen states (error, loading, empty, populated) and automatic scroll to the latest message.
- `chat-messages`: how user and assistant messages look and are aligned, and that message text is always displayed as plain text.
- `decision-card`: the passenger-facing summary of a disruption decision shown with an assistant message, limited to passenger-visible content.
- `chat-composer`: message input, sending, the 500-character limit and suggested questions.

### Modified Capabilities

None. There are no existing frontend specs. `passenger-communication` is not changed: the decision card follows its rules.

## Impact

- New directory `frontend/` with its own `package.json` and `pnpm-lock.yaml`; Node 24.22.1 or newer in the 24.x line, as in Cubik.
- New runtime dependencies: `react`, `react-dom`, `@mui/material`, `@mui/icons-material`, `@emotion/react`, `@emotion/styled`, and self-hosted Inter and Manrope fonts. MUI is large and increases the bundle size.
- Root `README.md` gets a frontend section; `frontend/README.md` is new.
- `.gitignore` needs the frontend build output and `node_modules`.
- No backend, API or Docker Compose change. The example data reuses the response shape of the existing endpoint, so a later connection change can pass real data through.
