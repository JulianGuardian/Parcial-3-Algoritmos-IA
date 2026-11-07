# Proposal

## Why

The backend already runs with `docker compose up --build`, in a non-root container with a health check and live reload. The frontend planned in `add-passenger-chat-ui` has no container, so a developer needs a local Node.js 24.22.1 and pnpm just to see the chat page, and the team cannot start the whole product with one command. This change gives the frontend the same one-command, reproducible local setup as the backend.

## What Changes

- Add `frontend/Dockerfile`: a development image based on `node:24.22.1-slim` (the version the frontend declares in `engines`) that installs dependencies from the lockfile and runs the Vite dev server as a non-root user.
- Add a `frontend` service to the root `docker-compose.yml`: port 5173, the frontend folder mounted for hot reload, and `node_modules` kept in a named volume so the host's modules are never used inside the container.
- The container runs `pnpm install --frozen-lockfile` before starting Vite, so changing dependencies and restarting brings the volume in line with the lockfile without rebuilding.
- File watching uses polling inside the container (enabled by an environment variable read by `vite.config.ts`), because change events do not cross Windows bind mounts.
- Add a health check that probes the dev server, and a `frontend/.dockerignore`.
- Pin the package manager with `packageManager` in `frontend/package.json` so the image and developers use the same pnpm version.
- Document running both services in the root `README.md` and `frontend/README.md`.

**Out of scope:** a production image (nginx or any static server), a reverse proxy or CORS setup between frontend and backend, environment variables for the API address, CI, and any cloud deployment. These belong to the change that connects the frontend to the backend.

**Depends on:** `add-passenger-chat-ui`. The `frontend/` package, its lockfile, `vite.config.ts` and its `dev` script must exist before this change is applied.

## Capabilities

### New Capabilities
- `frontend-containerization`: the Docker image and compose service that run the frontend development server reproducibly, as a non-root process, with hot reload and a health check.

### Modified Capabilities

None. `backend-containerization` keeps its requirements: adding a second service does not change how the backend is built, run or checked.

## Impact

- New files: `frontend/Dockerfile`, `frontend/.dockerignore`.
- Edited files: `docker-compose.yml` (new `frontend` service and `frontend_node_modules` volume), `frontend/vite.config.ts` (polling and host options driven by environment variables), `frontend/package.json` (`packageManager`), `README.md`, `frontend/README.md`.
- `docker compose up` now starts two services, and ports 8000 and 5173 must be free.
- First build downloads the Node image and installs dependencies, which takes longer than the backend build.
- No backend, API or application behavior changes.
