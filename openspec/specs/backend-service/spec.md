# backend-service Specification

## Purpose
Defines the base HTTP backend that future passenger-facing features build on: a versioned API, a liveness check, environment-driven configuration and correlated request logs for traceability.

## Requirements

### Requirement: Health endpoint
The system SHALL expose `GET /health` that returns HTTP 200 and a JSON body with `status` set to `"ok"` while the service is running, without requiring authentication or touching external systems.

#### Scenario: Service is running
- **WHEN** a client sends `GET /health`
- **THEN** the system responds with HTTP 200 and `{"status": "ok"}`

### Requirement: Versioned API prefix
The system SHALL serve all business endpoints under the `/api/v1` prefix, leaving `/health` and the API docs outside that prefix.

#### Scenario: Unversioned business route
- **WHEN** a client requests a business route without the `/api/v1` prefix
- **THEN** the system responds with HTTP 404

#### Scenario: Interactive API documentation
- **WHEN** a client sends `GET /docs`
- **THEN** the system responds with HTTP 200 and the OpenAPI documentation page

### Requirement: Environment-based configuration
The system SHALL read its configuration from environment variables, apply documented defaults for non-sensitive values, and refuse to start when a required value is missing or invalid.

#### Scenario: Override a setting
- **WHEN** the service starts with a supported setting defined in the environment
- **THEN** the service uses that value instead of the default

#### Scenario: Invalid configuration
- **WHEN** the service starts with an invalid value for a typed setting
- **THEN** the service exits with an error that names the offending setting

### Requirement: No secrets in the repository
The system SHALL ship only a `.env.example` containing placeholder values, and the real environment file SHALL be excluded from version control.

#### Scenario: Fresh clone
- **WHEN** a developer clones the repository
- **THEN** no real credentials are present and `.env.example` lists every supported setting with a placeholder

### Requirement: Correlated request logging
The system SHALL log every request as one structured JSON line including method, path, status code, duration and a request id, and SHALL return that id in the `X-Request-ID` response header, reusing the client's `X-Request-ID` when provided.

#### Scenario: Request without an id
- **WHEN** a client sends a request without `X-Request-ID`
- **THEN** the system generates an id, returns it in `X-Request-ID` and logs it with the request

#### Scenario: Request with an id
- **WHEN** a client sends a request with `X-Request-ID: abc-123`
- **THEN** the response header and the log line both carry `abc-123`

### Requirement: Safe error responses
The system SHALL return errors as JSON that never includes stack traces or internal details.

#### Scenario: Unhandled error
- **WHEN** an unexpected exception occurs while handling a request
- **THEN** the system responds with HTTP 500 and a generic JSON message plus the request id, and logs the details server-side
