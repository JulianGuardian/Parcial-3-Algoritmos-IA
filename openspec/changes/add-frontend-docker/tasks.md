# Tasks

## 1. Prerequisites and runtime pinning

- [x] 1.1 Confirm `add-passenger-chat-ui` is applied (`frontend/` with `package.json`, `pnpm-lock.yaml`, `vite.config.ts` and a working `dev` script) and add `"packageManager": "pnpm@10.33.0"` to `frontend/package.json`; verify `pnpm --version` inside `frontend/` prints `10.33.0` and `pnpm install --frozen-lockfile` still succeeds without changing the lockfile (`git status` shows only `package.json` modified)
- [x] 1.2 Extract a `watchOptions(env)` helper used by `vite.config.ts` that returns `{ usePolling: true, interval: 300 }` when `VITE_USE_POLLING` is `"true"` and `undefined` otherwise, and verify a unit test for both cases plus `pnpm run build`, `pnpm run lint` and `pnpm run test` passing

## 2. Development image

- [x] 2.1 Write `frontend/.dockerignore` (`node_modules`, `dist`, `.vite`, `.env`, `.env.*` except `.env.example`, `.git`, `coverage`, logs, `Dockerfile`, `.dockerignore`) and `frontend/Dockerfile` per design D1 and D5 (`node:24.22.1-slim`, Corepack, `node` user, cached install layer, sources copied, `EXPOSE 5173`, `HEALTHCHECK`, `CMD` running `pnpm run dev --host 0.0.0.0 --port 5173 --strictPort`); verify `docker build -t nubara-frontend:dev frontend` succeeds
- [x] 2.2 Verify the image alone: run it with port 5173 published and check that `curl http://localhost:5173` returns 200 with the page HTML, that `docker exec <c> id -u` is not `0`, that `node --version` satisfies `>=24.22.1 <25` and `pnpm --version` equals the `packageManager` value, and that `docker inspect` reports `healthy`
- [x] 2.3 Verify the build context is lean: with a host `frontend/node_modules`, `frontend/dist` and a `frontend/.env` present, rebuild and check that `docker run --rm --entrypoint sh nubara-frontend:dev -c "ls -a /app"` shows no `dist` and no `.env`, and that the build log reports a small context transfer (well under the size of the host `node_modules`)

## 3. Compose service

- [x] 3.1 Add the `frontend` service (build context `./frontend`, image `nubara-frontend:dev`, port `5173:5173`, `VITE_USE_POLLING=true`, source bind mount, `frontend_node_modules` named volume, the install-then-`exec` command from design D3) and the volume to `docker-compose.yml`; verify `docker compose config` is valid and `docker compose up --build` makes both `http://localhost:5173` and `http://localhost:8000/health` return 200
- [x] 3.2 Verify hot reload and host isolation: with the stack running and a host `frontend/node_modules` present, edit a visible string under `frontend/src` and check the change appears in the served module or in the Vite log within a few seconds, then revert the edit; check that `docker compose exec frontend ls -la node_modules` shows the container's own modules owned by `node`
- [x] 3.3 Verify dependency sync and service independence: add a small dev dependency on the host so the lockfile changes, run `docker compose restart frontend`, check the container installs it before starting (`docker compose exec frontend pnpm ls <package>`), and revert the dependency; check that `docker compose up --build backend` starts only the backend, still healthy

## 4. Documentation and final check

- [x] 4.1 Update the root `README.md` (both services, URLs `5173` and `8000`, starting one service, resetting dependencies with `docker compose down -v`, the Windows polling note and the Linux file-ownership note) and add a short "Docker" section to `frontend/README.md`; verify the documented commands run as written after `docker compose down -v`
- [x] 4.2 Verify the whole setup from a clean state: `docker compose down -v` then `docker compose up --build`, check that `docker compose ps` shows both services `healthy`, that `docker compose exec frontend pnpm run test` and `pnpm run lint` pass, and that the backend `pytest` suite is unaffected

## Workflow follow-up

- Archive the change after review (`/opsx:archive`).
