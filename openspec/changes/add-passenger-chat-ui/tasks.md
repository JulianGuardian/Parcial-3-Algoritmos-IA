# Tasks

## 1. Scaffold the frontend package

- [x] 1.1 Create `frontend/` with `package.json` (scripts `dev`, `build`, `lint`, `test`, `test:watch`, `preview`; `engines.node` `>=24.22.1 <25`; dependencies and dev dependencies from design D1 without KaTeX), `.nvmrc`, Vite, TypeScript, ESLint and Vitest configs, `index.html`, and add `frontend/node_modules/` and `frontend/dist/` to the root `.gitignore`; verify `pnpm install` succeeds and `git status` ignores `frontend/node_modules`
- [x] 1.2 Create the eight `src` folders with `.gitkeep` placeholders (`assets`, `components`, `hooks`, `icon`, `layouts`, `modules`, `routes`, `utils`), `setupTests.ts` and `testUtils.tsx`, and a minimal `App.tsx` and `main.tsx`; verify `pnpm run build`, `pnpm run lint` and `pnpm run test` (with one smoke test) all pass

## 2. Theme and shared components

- [x] 2.1 Implement `utils/theme.ts` (palettes, `createAppTheme` with the trimmed overrides, `warning` color and chip styles) and verify unit tests for both modes and for a contrast ratio of at least 4.5:1 for text, muted text and every status color against its background in both palettes
- [x] 2.2 Implement `AppThemeProvider` (follows `prefers-color-scheme` and its changes), `index.css`, and import the self-hosted `@fontsource-variable/inter` and `@fontsource-variable/manrope` in `main.tsx`; verify tests for dark, light and a preference change, and that the production build output contains no `fonts.googleapis.com` reference
- [x] 2.3 Implement `StatusBanner` and the `BotAvatarIcon` and `UserAvatarIcon` components, and verify component tests for banner text and severity and for the icons rendering with an accessible name

## 3. Chat model and helpers

- [x] 3.1 Define `modules/chat/types.ts` per design D4 and implement `utils/time.ts` (`formatClock`, `formatDate`), and verify unit tests that `2026-09-15T17:10:00` gives `17:10`, `2026-09-16` gives `16 Sep 2026`, and a browser time-zone change does not alter either result
- [x] 3.2 Implement `modules/chat/labels.ts` with the maps and fallbacks from design D5, and verify unit tests for every known code and for an unknown status, entitlement and human reason, none of which may return the raw code
- [x] 3.3 Write `modules/chat/fixtures.ts` (the ABC123 answer plus cancelled, unverified, compensation-requested and no-card variants) typed with `Message`, and verify `pnpm run build` type-checks it and a test that no fixture text contains `LEGACY_MIRROR`, `OPS_CORE`, `AIRPORT_FEED`, a rule identifier or the identity document number

## 4. Decision card

- [x] 4.1 Implement `DecisionCard` for the spec `decision-card` (sections and omission, flight status with delay and time, unverified handling, missed connection notice, benefits, no compensation amount, proposed option with "No extra cost", next step with plain reasons, monospace references, `region` role) and verify component tests for every scenario of the spec, including unknown entitlement and unknown reason fallbacks and "no internal strings for the sample booking"

## 5. Messages

- [x] 5.1 Implement `ChatMessage` (avatar, right/left alignment, system role as assistant, bubble colors, 78% width on wide screens, plain text with `pre-wrap`, card below the bubble only when a decision exists) and verify component tests for alignment, the system role, line breaks, `<img src=x onerror=alert(1)>` shown literally, and card present or absent
- [x] 5.2 Implement `EmptyConversationState` with the welcome message and the assistant avatar, and verify a component test for the welcome text and avatar

## 6. Composer

- [x] 6.1 Implement `Composer` with the multiline input, send button, Enter and Shift+Enter, IME guard, blank-text rules, reset after send, disabled state and accessible names, and verify component tests for each scenario of the spec including trimming `"  What are my options?  "` and the disabled state
- [x] 6.2 Add the 500-character limit and the counter from 400 characters, and verify tests for typing past the limit, pasting 700 characters, the counter appearing at 400 and not at 399, and the counter hiding after send
- [x] 6.3 Add the three suggestion chips that replace the input text, focus it and never submit, disabled with the composer, and verify tests for choosing a suggestion on an empty input and on an input that already has text

## 7. Page and application

- [x] 7.1 Implement `ChatPage` (bordered container, error banner, loading text, welcome, compact and wide padding, internal scroll, instant first scroll and smooth scroll on a new last message, `role="log"`) and verify component tests for loading, error, empty, populated, both scroll modes and that no `fetch` call is made
- [x] 7.2 Wire `App.tsx` (local state seeded from the fixtures, append the user's message on submit) and `main.tsx` (`AppThemeProvider`, fonts), and verify `pnpm run build`, `pnpm run lint` and `pnpm run test` pass and the dev server shows the chat page at its URL

## 8. Documentation and final check

- [x] 8.1 Write `frontend/README.md` (scripts, folder layout, how the example data works and that it is temporary) and add a frontend section to the root `README.md` in English, and verify the documented `pnpm` commands run as written from a clean `frontend/node_modules`
- [x] 8.2 Review the page in the dev server in the light and dark palettes and at phone and desktop widths, checking the welcome, every fixture variant, the card in all states and the composer limit, and verify the checklist has no unreadable text, no layout break and no third-party font request in the browser's network panel

## Workflow follow-up

- Archive the change after review (`/opsx:archive`).
