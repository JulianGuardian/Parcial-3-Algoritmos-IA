# Design

## Context

Greenfield repository: only `README.md` and `openspec/` exist. Motivation in proposal.md; behavior in the two specs. Project constraints that shape the approach: small team must operate it, personal data must be protected, traceability matters, and cost/latency/model dependency will matter later (so no LLM coupling in the base). Dev machines are Windows with Docker Desktop.

## Goals / Non-Goals

**Goals:**
- A runnable, tested FastAPI skeleton that a second developer can start with one command.
- Structure that lets domain modules (trips, modifications, handoff) be added without reorganizing.

**Non-Goals:**
- Persistence, auth, LLM integration, async job processing, production orchestration.

## Decisions

**Python 3.12 + FastAPI + Uvicorn.** Requested stack; typed models and automatic OpenAPI help a small team. Alternatives: Flask (no native validation/docs), Django (heavier than needed).

**Layout under `backend/`:**
```
backend/
  app/
    main.py          # app factory, middleware, router wiring
    api/health.py    # GET /health
    api/v1/router.py # empty /api/v1 router for future features
    core/config.py   # pydantic-settings Settings
    core/logging.py  # JSON logging + request-id middleware
  tests/test_health.py
  pyproject.toml
  Dockerfile
```
App factory (`create_app()`) keeps tests and config injection simple. Alternative: flat `main.py` — faster now, costly to refactor.

**Dependencies declared in `pyproject.toml`, installed with plain `pip`.** Plain `pip` with pinned versions keeps the Docker build simple and avoids another tool for the team to learn. Alternative: uv/poetry — better locking, but extra tooling; revisit if dependencies grow.

**Configuration with pydantic-settings.** Typed, validated at startup (fails fast per spec), `.env` loaded only for local dev. Alternative: raw `os.environ` — no validation.

**Structured JSON logs via stdlib `logging` + a custom formatter, request id in middleware using `contextvars`.** No extra dependency; satisfies the traceability goal and lets later layers (LLM calls, actions) log under the same id. Alternative: structlog — nicer API, additional dependency.

**Error handling:** global exception handler returns a generic 500 with the request id; details only in logs (avoids leaking internals or personal data).

**Docker:** multi-stage `python:3.12-slim` build, dependencies installed in a stage then copied, non-root user, `HEALTHCHECK` using Python stdlib (`urllib`) so `curl` isn't needed. Compose mounts `backend/app` and runs `uvicorn --reload` for dev; the image's default CMD runs without reload. Alternative: single-stage — simpler but larger image.

**Compose at repo root** (`docker-compose.yml`) so a later frontend or database service can join it.

## Risks / Trade-offs

- [Windows bind-mount reload can be slow or miss events] → Document it; plain `uvicorn --reload` (no `watchfiles` extra) uses a polling reloader, which works on bind mounts.
- [Plain pip without lockfile gives less reproducible builds] → Pin exact versions in `pyproject.toml`; adopt a lock tool once dependencies grow.
- [Logging request paths may capture personal data in query strings later] → Log path only, not query string or bodies; revisit when passenger data is introduced.
- [Over-structuring an empty skeleton] → Only create modules the specs require; `api/v1/router.py` stays empty.
