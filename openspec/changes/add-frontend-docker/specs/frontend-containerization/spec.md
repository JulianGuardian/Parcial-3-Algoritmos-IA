# Spec Delta

## Purpose

Defines how the frontend development server is packaged and run in a container so any developer can start an identical environment next to the backend with one command, as a non-root process.

## ADDED Requirements

### Requirement: Frontend development image
The system SHALL provide a Docker image that starts the frontend development server on port 5173, listening on all interfaces, with no manual steps beyond starting the container.

#### Scenario: Build and run the image
- **WHEN** a developer builds the image and runs it with port 5173 published
- **THEN** the chat page is served at `http://localhost:5173`

### Requirement: Pinned runtime versions
The image SHALL use a Node.js version inside the range declared by the frontend package and SHALL use the package manager version pinned in the package.

#### Scenario: Inspecting the runtime
- **WHEN** the container is running
- **THEN** its Node.js version satisfies the frontend `engines` range and its pnpm version equals the one in `packageManager`

### Requirement: Non-root runtime
The container SHALL run the development server as a non-root user.

#### Scenario: Inspect the process user
- **WHEN** the container is running
- **THEN** the development server process does not run as root

### Requirement: One-command local environment
The root compose definition SHALL start the frontend together with the backend with a single command, publish port 5173 for the frontend and keep the backend on port 8000.

#### Scenario: Start both services
- **WHEN** a developer runs `docker compose up --build`
- **THEN** the frontend is reachable at `http://localhost:5173` and the backend at `http://localhost:8000/health`

#### Scenario: Start only the backend
- **WHEN** a developer runs `docker compose up --build backend`
- **THEN** only the backend starts and it behaves as before

### Requirement: Hot reload from the host
The compose service SHALL mount the frontend sources and reload the browser view when a source file changes, including on hosts where file-system events do not cross bind mounts.

#### Scenario: Edit a source file while running
- **WHEN** a developer changes a file under `frontend/src` while the service is running
- **THEN** the served page reflects the change without rebuilding the image

### Requirement: Dependencies stay inside the container
The container SHALL use its own installed dependencies and SHALL NOT use a `node_modules` folder from the host. On start it SHALL install exactly what the lockfile declares.

#### Scenario: Host has its own node_modules
- **WHEN** the host has a `frontend/node_modules` folder and the service starts
- **THEN** the container does not use it and starts with dependencies installed for its own platform

#### Scenario: Dependency added after the first run
- **WHEN** the lockfile changes and the service is restarted
- **THEN** the container installs the new dependencies before starting the server, without rebuilding the image

### Requirement: Container health check
The image SHALL declare a health check that probes the development server, so the container reports `healthy` or `unhealthy`.

#### Scenario: Healthy container
- **WHEN** the development server is up
- **THEN** the container health status becomes `healthy`

### Requirement: Lean build context
The build SHALL exclude `node_modules`, build output, environment files and version-control data from the image.

#### Scenario: Local files present
- **WHEN** a developer has a `frontend/node_modules`, a `frontend/dist` and a local `.env` and builds the image
- **THEN** none of them is copied into the image
