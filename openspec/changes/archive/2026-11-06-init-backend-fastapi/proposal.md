# Proposal

## Why

The repository has no code yet. The Nubara Airlines flight-modification assistant needs a backend foundation before any passenger-facing capability (trip lookup, modification explanation, handoff) can be built. A small team must be able to run, test and deploy it identically on any machine, so the base must be containerized from day one.

## What Changes

- Add a Python backend project under `backend/` using FastAPI, with a layered package layout (`app/api`, `app/core`) ready for future domain modules.
- Add a liveness endpoint (`GET /health`) and a versioned API prefix (`/api/v1`) so later features plug in without breaking routes.
- Add environment-based configuration (typed settings, `.env.example`), with no secrets committed and no personal data handled at this stage.
- Add structured request logging with a request/correlation id, as the base for the traceability goal.
- Add a Dockerfile (slim image, non-root user) and a `docker-compose.yml` for local development with hot reload.
- Add a minimal test setup (pytest + FastAPI `TestClient`) covering the health endpoint.
- Add backend run instructions to the root `README.md`.

Out of scope: database, authentication, LLM/model integration, trip or booking logic, CI/CD, and cloud deployment.

## Capabilities

### New Capabilities
- `backend-service`: FastAPI application that exposes a health endpoint under a versioned API, loads configuration from the environment, and emits structured, correlated request logs.
- `backend-containerization`: Docker image and compose setup that runs the backend reproducibly for local development, as a non-root process.

### Modified Capabilities

## Impact

- New directory `backend/` (app code, tests, `pyproject.toml`/requirements, Dockerfile).
- New root files: `docker-compose.yml`, `.env.example`, `.dockerignore`; `README.md` updated.
- New dependencies: Python 3.12, FastAPI, Uvicorn, pydantic-settings, pytest, httpx.
- Requires Docker on developer machines. No existing code or specs are affected.
