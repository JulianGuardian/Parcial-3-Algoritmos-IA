# Spec Delta

## Purpose

Provides the runnable frontend package for the passenger assistant, so any developer can start, build, lint and test the application with documented commands and see the chat page.

## ADDED Requirements

### Requirement: Application runs in development mode
The frontend package SHALL provide a development server command that compiles and serves the application with TypeScript type checking.

#### Scenario: Starting the dev server
- **WHEN** a developer runs the dev script from the `frontend/` directory
- **THEN** a local development server starts and serves the application without compile errors

### Requirement: Application produces a production build
The frontend package SHALL provide a build command that type-checks the project and outputs a deployable production bundle.

#### Scenario: Running the build
- **WHEN** a developer runs the build script from the `frontend/` directory
- **THEN** the command completes successfully and emits static production assets to an output directory

### Requirement: Quality scripts
The frontend package SHALL provide a lint script and a test script that runs the automated tests once and exits with a failure status if any test fails.

#### Scenario: Running lint and tests
- **WHEN** a developer runs the lint script and the test script from `frontend/`
- **THEN** both complete successfully on a clean checkout

### Requirement: Root page renders the chat page
The application SHALL render the chat page as its root page content.

#### Scenario: Loading the application in a browser
- **WHEN** a user opens the application's served URL in a browser
- **THEN** the chat page is displayed with the messages area and the composer

### Requirement: Runtime version is declared
The frontend package SHALL declare the supported Node.js version range so that an unsupported version is reported instead of failing in unclear ways.

#### Scenario: Unsupported Node.js version
- **WHEN** a developer installs dependencies with a Node.js version outside the declared range
- **THEN** the package manager reports that the version is not supported
