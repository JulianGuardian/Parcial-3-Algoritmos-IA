# backend-containerization Specification

## Purpose
Defines how the backend is packaged and run in containers so any developer can start an identical environment with one command, with a least-privilege runtime.

## Requirements

### Requirement: Backend container image
The system SHALL provide a Docker image that starts the backend on port 8000 with no manual steps beyond supplying environment variables.

#### Scenario: Build and run the image
- **WHEN** a developer builds the image and runs it
- **THEN** `GET /health` on the published port responds with HTTP 200

### Requirement: Non-root runtime
The container SHALL run the application as a non-root user.

#### Scenario: Inspect the process user
- **WHEN** the container is running
- **THEN** the application process does not run as root

### Requirement: One-command local environment
The system SHALL provide a compose definition that builds and starts the backend with a single command, publishes port 8000 and reloads on source changes.

#### Scenario: Start with compose
- **WHEN** a developer runs `docker compose up --build`
- **THEN** the backend becomes reachable at `http://localhost:8000/health`

#### Scenario: Edit source while running
- **WHEN** a developer changes a file under `backend/app` while compose is running
- **THEN** the service reloads and serves the updated code

### Requirement: Container health check
The image SHALL declare a health check that probes the health endpoint, so the container reports `healthy` or `unhealthy`.

#### Scenario: Healthy container
- **WHEN** the service is up
- **THEN** the container health status becomes `healthy`

### Requirement: Lean build context
The build SHALL exclude local environment files, virtual environments, caches and version-control data from the image.

#### Scenario: Local secrets present
- **WHEN** a developer has a local `.env` file and builds the image
- **THEN** the image does not contain that file
