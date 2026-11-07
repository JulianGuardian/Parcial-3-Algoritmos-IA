# syntax=docker/dockerfile:1

# Development image: runs the Vite dev server with hot reload. There is no production image yet.
FROM node:24.22.1-slim

# pnpm comes from Corepack, at the version pinned in package.json ("packageManager").
RUN corepack enable

WORKDIR /app
RUN chown node:node /app
USER node

# Pin the pnpm store. With /app bind-mounted from the host, pnpm would otherwise pick a project-local
# /app/.pnpm-store (it prefers a store on the same device as the project). That does not match the
# store used by the install below, so pnpm asks to purge node_modules and aborts without a TTY.
ENV npm_config_store_dir=/home/node/.local/share/pnpm/store

# Dependencies get their own layer: it is cached until the manifest or the lockfile changes.
COPY --chown=node:node package.json pnpm-lock.yaml ./
# Running pnpm here makes Corepack download the pinned version at build time, not at container start.
RUN pnpm --version && pnpm install --frozen-lockfile

# Sources are copied so the image also runs on its own; compose mounts them over this for hot reload.
COPY --chown=node:node . .

EXPOSE 5173

# node:slim has no curl, so the check uses Node itself. The start period is long because compose
# runs an install before the server starts.
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:5173/').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"

CMD ["pnpm", "run", "dev", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
