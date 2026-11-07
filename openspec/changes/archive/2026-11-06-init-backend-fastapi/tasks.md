# Tasks

## 1. Project scaffold and configuration

- [x] 1.1 Create `backend/pyproject.toml` with pinned FastAPI, Uvicorn, pydantic-settings and dev deps (pytest, httpx); verify `pip install -e "backend[dev]"` succeeds in a fresh venv
- [x] 1.2 Create package layout (`backend/app/{api,api/v1,core}` with `__init__.py`) and verify `python -c "import app"` works from `backend/`
- [x] 1.3 Implement `app/core/config.py` (typed `Settings`, defaults, fail on invalid values) and verify unit tests cover default, override and invalid-value cases
- [x] 1.4 Add root `.env.example` listing every setting with placeholders, plus `.gitignore` entries for `.env`, venvs and caches; verify `git status` ignores a local `.env`

## 2. API, logging and errors

- [x] 2.1 Implement `app/main.py` `create_app()` and `GET /health`, mount empty `/api/v1` router; verify `tests/test_health.py` passes for `/health`, `/docs` and an unversioned business route returning 404
- [x] 2.2 Implement JSON logging and request-id middleware (`X-Request-ID` generated or reused, path logged without query string); verify tests assert header and log line for both cases
- [x] 2.3 Add global exception handler returning generic 500 JSON with request id; verify a test using a failing route shows no stack trace in the body and details in logs

## 3. Containerization

- [x] 3.1 Write `backend/Dockerfile` (multi-stage `python:3.12-slim`, non-root user, `HEALTHCHECK`, CMD without reload) and `.dockerignore`; verify `docker build` succeeds and `docker run` serves `/health` with 200
- [x] 3.2 Verify the container user is not root (`docker exec <c> id -u` is not `0`) and that `docker inspect` reports `healthy`
- [x] 3.3 Write root `docker-compose.yml` (build, port 8000, `./backend/app` bind mount, reload with polling, env file); verify `docker compose up --build` serves `http://localhost:8000/health` and that editing a file under `backend/app` triggers a reload
- [x] 3.4 Verify a local `.env` is absent from the built image (`docker run --rm <img> ls -a /app`)

## 4. Documentation and final check

- [x] 4.1 Update root `README.md` with local (venv) and Docker run instructions, test command and env settings; verify the documented commands run as written on a clean checkout
- [x] 4.2 Run the full test suite and `openspec validate init-backend-fastapi`; verify both pass

## Workflow follow-up

- Archive the change after review (`/opsx:archive`).
