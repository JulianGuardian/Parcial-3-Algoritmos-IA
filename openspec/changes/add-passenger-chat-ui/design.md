# Design

## Context

The repo has a FastAPI backend and no frontend. The backend already exposes `POST /api/v1/disruptions/{booking_id}/resolve`, which returns the assessment, the decision, the controlled actions and the passenger message. See proposal.md for the motivation.

Reference: the frontend of Cubik IA (`C:\dev\Cubik-IA\frontend`, React 19, Vite 8, TypeScript 6, MUI 9, Vitest 4), reviewed in its OpenSpec changes `add-chat-page-ui`, `add-src-folder-structure` and `add-frontend-hello-world`. Its design is kept: presentational chat page, light/dark theme from the system, local state over example data, tests next to the code. The math-specific parts are removed.

Constraints from this project that shape the port:
- The passenger may only see validated, policy-backed facts and minimal personal data (spec `passenger-communication`). The UI must not be able to show internal data even by mistake.
- Personal data must be protected, so the page must not send a request to a third party just to render (Cubik loads Google Fonts).
- The first version must be operable by a small team, so the setup stays close to Cubik's, which the team already knows.

Observed in the reference, relevant to the port:
- `Composer` in Cubik contains the calculator panel, the math preview, and snippet insertion; none apply here.
- `MathFormula` injects KaTeX HTML. Removing it also removes the only HTML-injection point of the chat.
- The 180-character rule that replaced long text with the resolution card has no meaning for the decision card.

## Goals / Non-Goals

**Goals:**
- Same look and interaction as Cubik for the page, the bubbles, the composer and the theme, in both palettes.
- A decision card that explains a disruption using only passenger-visible content.
- A pure UI: data in through props, events out through callbacks, so connecting the endpoint later does not rewrite components.
- Behavior from `specs/` covered by automated tests.

**Non-Goals:**
- Calling the backend, routing, authentication, a theme toggle, persisted theme, history, Docker Compose service, translations, code splitting.
- Showing agent traces, rejected options or any internal field, even behind a toggle.

## Decisions

### D1. Toolchain: Cubik's, minus KaTeX
Vite, React 19, TypeScript, MUI 9 with Emotion, ESLint flat config with `eslint-plugin-react-hooks`, Vitest with jsdom and Testing Library, pnpm. Versions follow Cubik's `package.json` and are re-checked at install. KaTeX and `@types/katex` are not installed. `engines.node` is `>=24.22.1 <25` with an `.nvmrc`, as in Cubik, and the current machine runs 24.22.1. Only pnpm is used (the repository's tooling rejects npm).
*Alternative:* Create React App or Next.js (rejected: heavier than a static SPA needs and unknown to the team).

### D2. File layout (follows `frontend-src-layout`)

```
frontend/
  package.json  vite.config.ts  tsconfig*.json  eslint.config.js  index.html  .nvmrc  README.md
  src/
    main.tsx                    mounts AppThemeProvider > App, imports the self-hosted fonts
    App.tsx                     owns local message state, renders ChatPage
    index.css                   resets and scrollbars
    setupTests.ts  testUtils.tsx
    assets/ hooks/ layouts/ routes/        (.gitkeep until used)
    components/
      AppThemeProvider/         ThemeProvider + CssBaseline, follows the system scheme
      StatusBanner/             error/info alert
    icon/                       BotAvatarIcon, UserAvatarIcon, IconProps
    utils/
      theme.ts                  palettes + createAppTheme
      time.ts                   formatClock, formatDate (pure)
    modules/chat/
      ChatPage.tsx
      components/               ChatMessage, DecisionCard, Composer, EmptyConversationState
      labels.ts                 plain-language labels for status, entitlements, human reasons
      fixtures.ts               example conversation (temporary)
      types.ts                  Message, DisruptionDecision (UI subset of the API response)
      index.ts
```

`StatusBanner` and the theme provider go in `components/` because they have no chat knowledge. `DecisionCard` stays in the module: only messages use it, and it knows the disruption vocabulary.

### D3. Presentational page
`ChatPage` props: `messages`, `isLoading` (default false), `error` (default null), `isSubmitting` (default false), `onSubmit(text)`. `App.tsx` holds `useState` for the messages, seeded from `fixtures.ts`, and appends the user's message on submit. No hook, no fake API. Loading and error are reachable through props and covered by tests.
*Alternative:* a fake API client (rejected: it reintroduces connection logic that is out of scope).

### D4. UI model mirrors the real response, trimmed
`types.ts` declares only what the passenger may see, with the API's snake_case names and nesting, so a later change can pass the response through with a small mapping:

- `Message { id, role: "user" | "assistant" | "system", content, decision? }`
- `DisruptionDecision`:
  - `assessment.segments[]`: `segment_id`, `flight_number`, `origin`, `destination`, `status`, `delay_minutes`, `estimated_departure`, `missed_connection`;
  - `decision.applied_rules[]`: `entitlement` only; `decision.recommended_option` (`flight_number`, `origin`, `destination`, `date`, `departure`, `fare_difference`); `decision.requires_human`; `decision.human_reasons[]`; `decision.policy_ref`;
  - `actions.human_case?`: `case_id`.
- `Message.content` carries `notification.text`.

Fields such as `discarded_events`, `rejected_options`, `trace`, `rule_id` and option `confidence` do not exist in the type, so the card cannot render them and a fixture cannot include them without a type error. This is the compile-time half of "internal data is never shown"; a render test is the runtime half.
*Alternative:* import the full response type (rejected: it makes leaking one `JSON.stringify` away).

### D5. Plain-language labels with safe fallbacks
`labels.ts` maps backend codes to text, and every lookup has a fallback that never prints the raw code:

| Kind | Code | Text |
|---|---|---|
| Status | `SCHEDULED`, `ON_TIME` | On schedule |
| Status | `DELAYED` | Delayed |
| Status | `CANCELLED` | Cancelled |
| Status | `CONFLICTING`, `UNVERIFIED`, unknown | Being confirmed |
| Entitlement | `REBOOK_NO_FEE` | Free rebooking |
| Entitlement | `MEAL_VOUCHER` | Meal voucher |
| Entitlement | `PRIORITY_HANDLING` | Priority handling |
| Entitlement | `CASH_COMPENSATION` | Compensation request: an agent will review it |
| Entitlement | unknown | Additional benefit: an agent will give you details |
| Human reason | `R5_PRIORITY_HANDLING` | Priority handling for travellers with a minor |
| Human reason | `R4_CASH_COMPENSATION` | Your compensation request needs an agent's review |
| Human reason | `ASSESSMENT_CONFLICTING`, `ASSESSMENT_UNVERIFIED` | We are still confirming the status of your trip |
| Human reason | `MISSING_DECISION_DATA` | Some booking details need to be checked |
| Human reason | unknown | An agent needs to review your case |

Unverified statuses also hide delay minutes and times (spec `decision-card`), because those facts did not pass validation. The card never states that the booking changed and never gives a compensation amount.

### D6. Times and dates are shown as given
Estimated times arrive as airport-local ISO strings. `formatClock` reads the `HH:MM` part of the string and `formatDate` formats `YYYY-MM-DD` with a fixed month table, so no `Date` conversion shifts them by the browser's time zone. Both are pure functions in `utils/time.ts` with unit tests.
*Alternative:* `Intl.DateTimeFormat` on `new Date(iso)` (rejected: converts to the viewer's zone and would show wrong local times).

### D7. Message text is plain text
Text goes through React as a text node with `white-space: pre-wrap` to keep line breaks. There is no Markdown, no link detection and no `dangerouslySetInnerHTML` anywhere. A test renders `<img src=x onerror=...>` and checks it appears literally.

### D8. Theme and fonts
Port `createAppTheme` and the Cubik palette (primary `#1547A1` light / `#3B82F6` dark, same surfaces), trimmed to overrides for components that exist here: `CssBaseline`, `Paper` (1px border, palette shadow, no background image), `Button`, `Alert`, `Tooltip`, `Chip`. Adds a `warning` color for "Delayed" and a neutral chip for "Being confirmed". Mode comes from `matchMedia("(prefers-color-scheme: dark)")` with a change listener; no toggle and no `localStorage`.

Fonts are self-hosted with `@fontsource-variable/inter` and `@fontsource-variable/manrope`, imported in `main.tsx`, instead of Cubik's Google Fonts `@import`. This avoids a request to a third party and works offline. References (booking, case, policy) use the system monospace stack, so no third font is shipped.

A unit test computes the WCAG contrast ratio of text, muted text and each status color against their backgrounds in both palettes and requires at least 4.5:1, which turns "readable text in both palettes" into a check instead of an eyeball.

### D9. Composer
Ported from Cubik: multiline `TextField` growing to six rows, Enter sends, Shift+Enter inserts a line break, Enter is ignored during IME composition, blank text is not sendable, input clears after sending, disabled state.
Removed: calculator button and keyboard, math preview, snippet insertion, attach and OCR leftovers.
Added:
- `maxLength` of 500 matching the backend `question` limit, plus a defensive `slice(0, 500)` in the change handler, and a counter shown from 400 characters;
- three suggestion chips that set the input text (replacing it) and focus it, without sending; they are disabled with the composer.

### D10. Auto-scroll and accessibility
Same behavior as Cubik: one effect and an end-of-list sentinel, instant on first display and smooth when the last message id changes. The messages area is `role="log"` with polite live updates, the send button has `aria-label="Send message"`, the input has an accessible name, the decision card is a `region` named by its title, and statuses are text, never color alone.

### D11. Example data
`fixtures.ts` holds the conversation used by `App.tsx`: a question and the full ABC123 answer (delay of 160 minutes, missed connection to NB2410, free rebooking and priority handling, O1 proposed, agent follow-up, case reference and policy reference), plus variants so every card state can be reviewed: cancelled flight, unverified status, compensation requested, and an assistant message without a card. Values are hand-copied from the endpoint's response shape and contain no internal fields; the only personal data is the first name inside the message text. The file is temporary: the connection change removes it together with the seeding in `App.tsx`.

### D12. Tests
Vitest with jsdom and Testing Library, `test` script. Unit tests: `time.ts`, `labels.ts`, `theme.ts` (including contrast). Component tests: `Composer` (send, trim, Enter, Shift+Enter, IME, limit, counter, paste, suggestions, disabled), `ChatMessage` (alignment, plain text, HTML literal, card or not), `DecisionCard` (every spec scenario, fallbacks, forbidden strings absent for the sample booking), `ChatPage` (loading, error, empty, scroll calls), `AppThemeProvider` (dark, light, change), `StatusBanner`. Visual fidelity is checked by eye in the dev server, once per palette.

### D13. Docs and ignores
`frontend/README.md` (scripts, layout, how the example data works) and a short frontend section in the root `README.md`. The root `.gitignore` gains `frontend/node_modules/` and `frontend/dist/`.

## Risks / Trade-offs

- [Example data drifts from the real response shape] → The UI types mirror the response and fixtures are typed, so a shape change breaks `tsc`; the connection change replaces the fixtures with real calls.
- [MUI v9 API differs from older examples online] → The port starts from Cubik's v9 code and uses `slotProps` and the current `Grid` API.
- [`eslint-plugin-react-hooks` v7 flags patterns such as setting state inside effects] → Derive state or handle it in event handlers; do not disable rules.
- [Bundle size grows with MUI, Emotion and the two variable fonts] → Import icons from `@mui/icons-material/<Name>`, never the barrel; measure with `pnpm run build`; code splitting later.
- [English-only text while the team and airline context is Spanish-speaking] → Chosen to match the backend messages and avoid a mixed-language screen; copy lives in few files (`labels.ts`, components) so adding i18n later is mechanical.
- [A label gap lets an unknown backend code reach the passenger] → Every lookup has a generic fallback and a test pins it.
- [Contrast ratios in the dark palette can fail for the warning color] → Caught by the contrast test, not by eye.
- [Node 24.22.1 is required, as in Cubik] → Declared in `engines` and `.nvmrc`; contributors on older Node get a warning at install.

## Open Questions

- In the connected version, where does the booking id come from (a field in the page, a URL parameter, or the signed-in passenger)? This does not change this change, because the page receives messages through props.
