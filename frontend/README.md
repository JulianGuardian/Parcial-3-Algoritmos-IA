# Nubara passenger frontend

React 19 + TypeScript + Vite. Package manager: pnpm. Node.js 24.22.1 or newer in the 24.x line (see `.nvmrc`).

The page is the chat where a passenger asks about a flight change and reads what happened and what to do next. It talks to the conversational agent through `src/api/` (`/api/v1/conversations`). The dev server proxies `/api` to `API_PROXY_TARGET` (default `http://localhost:8000`), and `VITE_DEMO_NOW`, if set, pins the evaluation time sent with each message. The example data in `src/modules/chat/fixtures.ts` is used by the tests only.

## Scripts

Run scripts from this folder with `pnpm run <script>`.

| Script | What it does |
|---|---|
| `pnpm run dev` | Vite dev server at <http://localhost:5173> |
| `pnpm run build` | Type-check (`tsc -b`) and production build to `dist/` |
| `pnpm run lint` | ESLint |
| `pnpm run test` | Vitest (jsdom + Testing Library), single run |
| `pnpm run test:watch` | Vitest in watch mode |
| `pnpm run preview` | Serve the production build |

First time: `pnpm install`. Tests live next to the code as `*.test.ts(x)`; shared setup is in `src/setupTests.ts`.

## Docker

From the repository root, `docker compose up --build` starts this app together with the backend. The frontend is at <http://localhost:5173>; start only it with `docker compose up --build frontend`.

- `frontend/Dockerfile` is a development image (Node 24.22.1, pnpm from Corepack at the version in `packageManager`, non-root user, health check). There is no production image yet.
- The folder is mounted, so edits reload the page. Vite polls for changes (`VITE_USE_POLLING=true`, read in `vite.config.ts`) because file events do not cross a Windows bind mount.
- Dependencies are installed inside the container into the `frontend_node_modules` volume and are never taken from your `node_modules`. After changing `package.json`, restart with `docker compose restart frontend`; to start from scratch use `docker compose down -v`.

More in the root [`README.md`](../README.md).

## Source layout

| Path | Contents |
|---|---|
| `src/modules/chat/` | Chat page: `ChatPage`, `ChatMessage`, `DecisionCard`, `Composer`, `EmptyConversationState`, plus `types.ts`, `labels.ts` and `fixtures.ts` |
| `src/components/` | Shared UI with no chat knowledge: `AppThemeProvider` (light/dark from the system) and `StatusBanner` |
| `src/utils/` | `theme.ts` (palettes and MUI theme) and `time.ts` (shows airport-local times as given) |
| `src/icon/` | Avatar icons |
| `src/assets`, `hooks`, `layouts`, `routes` | Empty for now (`.gitkeep`), reserved by the folder layout |

## How the page works

The chat page is presentational. It gets `messages`, `isLoading`, `error`, `isSubmitting`, `onSubmit`, `onConfirm` and an optional `footer` as props; the footer replaces the composer, and the booking step uses it.

`src/App.tsx` holds the conversation:
1. **Booking step.** `BookingForm` starts the conversation with `startConversation`.
2. **Messages.** Each message goes through `sendMessage`, and the answer is mapped to the card by `api/mapper.ts`.
3. **Confirmation.** It is sent with `confirm_option_id`, and only the latest answer offers it.
4. **Errors.** A `404 CONVERSATION_NOT_FOUND` returns to the booking step. Any other error shows a banner and keeps the typed text.

The examples in `src/modules/chat/fixtures.ts` cover every card state and are used by the tests only.

Assistant messages can carry a decision card. `src/modules/chat/types.ts` is the card's view model, filled from the agent response (`src/api/types.ts`) and trimmed to what a passenger may see: internal sources, discarded events, rejected options, rule identifiers and the trace are not in the types, so the card cannot show them. Backend codes are translated to plain words in `labels.ts`, and an unknown code is shown as a generic text, never as the code.

Message text is always displayed as plain text; nothing in it is interpreted as HTML or markup.

## Fonts

Inter and Manrope are self-hosted through `@fontsource-variable/inter` and `@fontsource-variable/manrope`, so the page makes no request to a third party for fonts.

## Specs

Behavior is specified with OpenSpec in the repository's `openspec/` folder (`specs/` for current requirements, `changes/` for work in progress).
