# Design

## Context

Current state (observed):
- `docker-compose.yml` has one service, `backend`: it builds `backend/Dockerfile`, publishes 8000, mounts `backend/app` and overrides the image command to add `--reload`, relying on uvicorn's polling reloader so it works on Windows bind mounts.
- `backend/Dockerfile` is a two-stage image with a non-root user, a `HEALTHCHECK` and a lean `.dockerignore`. Spec `backend-containerization` describes it.
- There is no `frontend/` yet. It is planned in `add-passenger-chat-ui` (Vite, React 19, pnpm, `engines.node` `>=24.22.1 <25`, scripts `dev`, `build`, `lint`, `test`), so this change is applied after it.
- The development machines are Windows with Docker Desktop. The repository's tooling rejects `npm`, so everything uses pnpm.
- The Cubik IA project has no frontend container, so there is no earlier design to reuse; this one copies the backend's pattern.

Scope was chosen with the user: development only (see proposal.md).

## Goals / Non-Goals

**Goals:**
- `docker compose up --build` starts frontend and backend; the frontend at `http://localhost:5173` reloads on edits.
- Same standards as the backend container: non-root, health check, lean build context, pinned runtime.
- Reproducible installs: the container never uses the host's `node_modules`.

**Non-Goals:**
- A production image, a static server, a reverse proxy, CORS, API address variables, CI or deployment.
- `docker compose watch` or any file-sync mechanism other than a bind mount.

## Decisions

### D1. A development image built from `node:24.22.1-slim`
`frontend/Dockerfile` is a single stage:
1. `FROM node:24.22.1-slim` (verified to exist; matches the lower bound of `engines`).
2. `RUN corepack enable` as root so the `pnpm` shim exists.
3. `WORKDIR /app`, owned by the `node` user (already in the image, uid 1000), and `USER node`.
3b. `ENV npm_config_store_dir=/home/node/.local/share/pnpm/store`, which pins the pnpm store. Found while applying this change: when `/app` is a bind mount from the host, pnpm prefers a store on the same device as the project and creates `/app/.pnpm-store`, which no longer matches the store of the install made at build time. pnpm then asks to purge `node_modules`, and aborts without a TTY (`ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`), so the container exits. With the store pinned, the startup install finds nothing to change.
4. Copy only `package.json` and `pnpm-lock.yaml`, then `RUN pnpm install --frozen-lockfile`. This layer is cached until the manifest or lockfile changes. A `RUN pnpm --version` first makes Corepack download the pinned pnpm at build time, not at start.
5. Copy the rest of the sources with `--chown=node:node`, so `docker run` works on its own, without compose.
6. `EXPOSE 5173`, a `HEALTHCHECK` and a `CMD` that runs `pnpm run dev` with `--host 0.0.0.0 --port 5173 --strictPort`.

*Alternatives:* run a bare `node` image from compose with an install on every start (rejected: slow and not reproducible without an image); multi-stage with nginx (out of scope by decision).

### D2. Pin pnpm with `packageManager`
`frontend/package.json` gets `"packageManager": "pnpm@10.33.0"`, the version the team uses today. Corepack reads it, so the image and a developer's machine run the same pnpm, and `--frozen-lockfile` sees the same lockfile format. Bumping pnpm is a one-line change plus a lockfile refresh.

### D3. Compose service, with `node_modules` in a named volume
```
frontend:
  build: { context: ./frontend }
  image: nubara-frontend:dev
  ports: ["5173:5173"]
  environment: { VITE_USE_POLLING: "true" }
  volumes:
    - ./frontend:/app                              # sources, for hot reload
    - frontend_node_modules:/app/node_modules      # container-owned dependencies
  command: ["sh", "-c", "pnpm install --frozen-lockfile && exec pnpm run dev --host 0.0.0.0 --port 5173 --strictPort"]
volumes:
  frontend_node_modules:
```
- **Why a named volume.** Bind-mounting `./frontend` would hide the image's `node_modules` and expose the host's, whose native binaries (the bundler and compiler) are built for Windows. The named volume layers over that path and is filled from the image on first use, keeping the `node` ownership.
- **Why install on start.** A named volume does not follow image rebuilds, so after a dependency change it would hold stale modules. Running `pnpm install --frozen-lockfile` before the server fixes that without `down -v`, and it finishes in about a second when nothing changed. If `package.json` and the lockfile disagree the command fails loudly, which is the desired behavior.
- **`exec`** makes Vite PID 1 so `docker compose stop` sends it the signal directly.
- No `depends_on`: the page is a pure UI and does not call the backend yet. `docker compose up --build backend` still starts only the backend.

*Alternatives:* `docker compose watch` with `develop.watch` sync rules (rejected for now: needs a newer Compose, behaves differently from the backend's mount, and syncing `node_modules` rules are fiddly; revisit if mounts prove slow); an anonymous volume for `node_modules` (rejected: it is recreated on every `up` and loses the install).

### D4. Polling for file watching, driven by an environment variable
File-system events do not cross a Windows bind mount, so Vite never sees edits. `vite.config.ts` reads `VITE_USE_POLLING` and, when it is `"true"`, sets `server.watch` to `{ usePolling: true, interval: 300 }`. Compose sets it; a local run without Docker does not, so native watching keeps working. The HMR WebSocket needs no extra setting: the browser reaches Vite on the same published port, `localhost:5173`.

### D5. Health check without extra packages
`node:24-slim` has no `curl`. The check uses Node itself, like the backend uses Python:
`node -e "fetch('http://127.0.0.1:5173/').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"`, with `--interval=30s --timeout=3s --retries=3` and a `--start-period` of 60 seconds, longer than the backend's because the first start installs dependencies.

### D6. Lean build context
`frontend/.dockerignore` excludes `node_modules`, `dist`, `.vite`, `.env` and `.env.*` except `.env.example`, `.git`, `coverage`, logs, `Dockerfile` and `.dockerignore`. Excluding `node_modules` also keeps a host install from inflating the build or leaking Windows binaries into the Linux image.

### D7. Documentation
The root `README.md` explains that `docker compose up --build` starts both services, lists the two URLs, how to start one service, how to reset dependencies (`docker compose down -v`) and the Windows polling note. `frontend/README.md` gets a short "Docker" section linking to it.

## Risks / Trade-offs

- [First build and first start are slow: Node image, Corepack download and a full install] → Layer caching and the named volume make later starts fast; the health check start period is 60 s.
- [Bind-mounted files may not be writable by uid 1000 on Linux hosts, which breaks Vite's temporary config file] → Not an issue on Docker Desktop for Windows or macOS, which are the team's machines; Linux contributors can set `user` in a local compose override. Noted in the README.
- [Polling uses some CPU] → A 300 ms interval is a compromise; only active in containers.
- [pnpm creating a store inside the host folder when the pinned store is lost] → The pin lives in the image; if a `frontend/.pnpm-store` ever appears it is safe to delete and is ignored by Git and by `.dockerignore`.
- [A stale `frontend_node_modules` volume after an interrupted install] → `docker compose down -v` resets it; documented.
- [Corepack needs network access at build time] → Acceptable for a development image; the layer is cached afterwards.
- [pnpm 10 blocks dependency build scripts by default, which could skip a needed post-install step] → Checked when the image is first built: the frontend must start and pass its tests inside the container; any approval needed is declared in `package.json`.
- [Two services on ports 5173 and 8000 can collide with other local tools] → Documented; the mapping is one line in compose.
- [This change edits `vite.config.ts` and `package.json` owned by `add-passenger-chat-ui`] → Applied after that change, with small, isolated edits.
