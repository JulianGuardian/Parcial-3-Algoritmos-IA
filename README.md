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

The work is specified with [OpenSpec](https://github.com/Fission-AI/OpenSpec) in `openspec/changes/resolve-passenger-disruption/` (proposal, specs, design and tasks). The domain lives in `backend/app/disruption/` as plain Python with no FastAPI imports, so each layer is tested without HTTP.

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

## How to run the project

### Requirements

| Tool | Version | Needed for |
|------|---------|------------|
| Git | any | cloning the repo |
| Docker Desktop (or Docker Engine + Compose v2) | Compose ≥ 2.24 | running with Docker |
| Python | 3.12 or higher | running without Docker and tests |

You do not need to install Python if you run with Docker.

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

- Backend at <http://localhost:8000> and documentation at <http://localhost:8000/docs>.
- The `backend/app` code is mounted: saving a file reloads the service automatically.
- To run it in the background: `docker compose up --build -d`, and follow the logs with `docker compose logs -f backend`.
- To stop it: `Ctrl+C` (or `docker compose down` if you used `-d`).

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
| `ValidationError ... log_level` at startup | Invalid value in `.env`. Use one of the values in the configuration table. |
| `env_file ... required` not supported | Old Compose version. Update Docker Desktop (Compose ≥ 2.24). |
| Reload does not detect changes on Windows | A polling reloader is used; wait 1–2 seconds after saving. |
