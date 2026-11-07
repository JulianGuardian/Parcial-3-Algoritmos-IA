# Parcial 3 – Algoritmos - IA

Third midterm project for the Algorithms - Artificial Intelligence course.

Repository: <https://github.com/JulianGuardian/Parcial-3-Algoritmos-IA>

## Backend (FastAPI)

Base service in `backend/` (Python 3.12+, FastAPI). Endpoints:

| Route | Description |
|-------|-------------|
| `GET /health` | Liveness: `{"status": "ok"}` |
| `GET /docs` | Interactive OpenAPI documentation |
| `/api/v1/...` | Prefix for business endpoints (still empty) |

Every response includes the `X-Request-ID` header (the client's value is reused if it is valid) and every request is logged as one JSON line to stdout.

## Passenger disruption domain

The backend is the base of a Nubara Airlines feature that helps passengers whose flight was modified: it explains what happened and what to do next, without giving unverified information and without executing high-impact actions (rebooking, compensation) without human approval.

The work is specified with [OpenSpec](https://github.com/Fission-AI/OpenSpec) in `openspec/changes/archive/2026-11-06-resolve-passenger-disruption/` (proposal, design and tasks) and the main specs in `openspec/specs/`. The change was archived with its tasks 4 to 7 still pending; move it back to `openspec/changes/` to keep implementing them. The domain lives in `backend/app/disruption/` as plain Python with no FastAPI imports, so each layer is tested without HTTP.

| Layer | Package | Status | What it does |
|-------|---------|--------|--------------|
| Contracts | `contracts.py` | done | Dataclasses shared by all layers: `ResolveRequest`, `TripState`, `Decision`, `RejectedOption`, `TraceEntry` |
| Assessment | `assessment/` | done | Strips personal data, reconciles sources (priority, degraded, stale, conflicts), detects missed connections and relevance |
| Entitlements | `entitlements/` | done | Evaluates policy rules R1–R5, filters options with reason codes, recommends one and decides when a human must approve |
| Intake | `intake/` | pending | Classifies a free-text question into intents |
| Actions | `actions/` | pending | Controlled writes: rebooking request, human case, idempotency |
| Communication | `communication/` | pending | Validated passenger messages |
| Answer agent | `agents/` | pending | Question-specific answers over safe read-only tools |
| HTTP endpoint | `app/api/v1/` | pending | `POST /api/v1/disruptions/{booking_id}/resolve` |

The assessment and entitlements layers run today against mock tools that return the exam's sample responses (`backend/app/disruption/fixtures/`, booking `ABC123`). They are not exposed over HTTP yet; the layer tests are the way to exercise them.

Key decisions (details in `design.md`):
- Operational sources are ranked `OPS_CORE` > `AIRPORT_FEED` > `LEGACY_MIRROR`; degraded sources and events older than 2 hours are never trusted, and a disagreement between `OPS_CORE` and `AIRPORT_FEED` is `CONFLICTING` and goes to a human.
- A missed connection is derived from the delay and a 60-minute minimum connection time, so a delay below the policy thresholds can still create an entitlement.
- Options past their TTL, without seats for the whole party, contradicting the applied entitlement, or with low confidence are never recommended.
- A human must approve whenever a rule requires it (R4, R5), the assessment is `CONFLICTING` or `UNVERIFIED`, or data the decision needs is missing.

## Frontend (React + Vite)

The passenger chat lives in `frontend/` (React 19, TypeScript, Vite, MUI, pnpm). It shows the conversation and, under each assistant answer, a card that explains the disruption: what happened to each flight, the passenger's benefits, the proposed option at no extra cost and whether an agent will follow up. The card shows only what a passenger may see.

The screen is a pure UI for now: it makes no API calls and shows example data shaped like the response of `POST /api/v1/disruptions/{booking_id}/resolve`. Connecting it to the backend is a later change. The interface text is in English and the theme follows the system's light or dark preference.

The easiest way to run it is with Docker together with the backend (see [Run with Docker](#3a-run-with-docker-recommended)). To run it on its own you need Node.js 24.22.1 or newer in the 24.x line and pnpm (see `frontend/.nvmrc`):

```bash
cd frontend
pnpm install
pnpm run dev        # http://localhost:5173
pnpm run test       # unit and component tests
pnpm run build      # type-check and production build
```

More details in [`frontend/README.md`](frontend/README.md).

## How to run the project

### Requirements

| Tool | Version | Needed for |
|------|---------|------------|
| Git | any | cloning the repo |
| Docker Desktop (or Docker Engine + Compose v2) | Compose ≥ 2.24 | running with Docker |
| Python | 3.12 or higher | running the backend without Docker and its tests |
| Node.js + pnpm | 24.22.1 or newer in 24.x, pnpm 10.33.0 | running the frontend without Docker and its tests |

You do not need to install Python or Node.js if you run with Docker.

### 1. Clone the repository

```bash
git clone https://github.com/JulianGuardian/Parcial-3-Algoritmos-IA.git
cd Parcial-3-Algoritmos-IA
```

### 2. Configure environment variables (optional)

The service starts with default values. To change them:

```bash
cp .env.example .env         # Windows (PowerShell): Copy-Item .env.example .env
```

Edit `.env` using the [Configuration](#configuration) table. The real `.env` is never committed.

### 3a. Run with Docker (recommended)

Open Docker Desktop and wait until the engine is running. Then, from the repo root:

```bash
docker compose up --build
```

This starts two services:

| Service | URL | Notes |
|---------|-----|-------|
| `backend` | <http://localhost:8000> (docs at <http://localhost:8000/docs>) | FastAPI; `backend/app` is mounted, so saving a file reloads it |
| `frontend` | <http://localhost:5173> | Vite dev server; `frontend/` is mounted, so saving a file updates the page without a rebuild |

- The first start is slower: it downloads the Node image and installs the frontend dependencies inside the container.
- The container uses its own `node_modules` (a Docker volume), never the one on your machine. If you change dependencies in `frontend/package.json`, restart the service (`docker compose restart frontend`) and it installs what the lockfile says.
- To start only one service: `docker compose up --build backend` or `docker compose up --build frontend`.
- To run it in the background: `docker compose up --build -d`, and follow the logs with `docker compose logs -f frontend` (or `backend`).
- To stop it: `Ctrl+C` (or `docker compose down` if you used `-d`). To also reset the frontend dependencies, use `docker compose down -v`.
- On Linux the container user (uid 1000) must be able to write in `frontend/`; if your user has a different uid, set `user` for the service in a local compose override.

### 3b. Run without Docker

From the `backend/` folder:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```bash
.venv\Scripts\activate        # Windows (cmd/PowerShell)
source .venv/bin/activate     # Linux / macOS / Git Bash: source .venv/Scripts/activate
```

Install dependencies and start the server:

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The service is available at <http://127.0.0.1:8000>. To stop it: `Ctrl+C`. If you have a `.env` in the repo root, copy it to `backend/` or export the variables, because without Docker `.env` is read from the directory where you run `uvicorn`.

### 4. Check that it works

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Or open <http://localhost:8000/docs> in your browser. To see the `X-Request-ID` header in the response:

```bash
curl -i -H "X-Request-ID: my-test-1" http://localhost:8000/health
```

For the frontend, open <http://localhost:5173>: you should see the chat with the example conversation.

### Tests

With the virtual environment active, from `backend/`:

```bash
pytest                      # everything
pytest tests/disruption     # only the passenger disruption domain
```

The domain tests need no network, Docker or API key: they use the sample fixtures.

### Configuration

Environment variables (see `.env.example`):

| Variable | Values | Default |
|----------|--------|---------|
| `APP_NAME` | text | `nubara-backend` |
| `ENVIRONMENT` | `local`, `staging`, `production` | `local` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `API_V1_PREFIX` | path | `/api/v1` |

An invalid value makes the service fail at startup and name the offending variable.

### Troubleshooting

| Symptom | Cause and fix |
|---------|---------------|
| `failed to connect to the docker API` | Docker Desktop is not running. Open it and wait for "Engine running". |
| `port is already allocated` / port 8000 in use | Another process is using port 8000. Stop it or change the mapping in `docker-compose.yml` (for example `"8001:8000"`). |
| Port 5173 in use (the frontend exits with `Port 5173 is already in use`) | Another Vite or tool uses 5173. Stop it or change the mapping in `docker-compose.yml`. |
| `ERR_PNPM_...` in `docker compose logs frontend`, or a dependency that is missing | The `frontend_node_modules` volume is out of date or was interrupted. Run `docker compose down -v` and start again. |
| `ValidationError ... log_level` at startup | Invalid value in `.env`. Use one of the values in the configuration table. |
| `env_file ... required` not supported | Old Compose version. Update Docker Desktop (Compose ≥ 2.24). |
| Reload does not detect changes on Windows | Both services use a polling reloader because file events do not cross the Windows mount; wait 1–2 seconds after saving. |
