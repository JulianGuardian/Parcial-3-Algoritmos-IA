# Spec Delta

## Purpose

Defines the folder structure of the frontend `src` directory and what each folder is responsible for, so contributors always know where a new file belongs.

## ADDED Requirements

### Requirement: Source directory provides the standard folders
The frontend `src` directory SHALL contain these top-level folders: `assets`, `components`, `hooks`, `icon`, `layouts`, `modules`, `routes`, `utils`.

#### Scenario: Listing the source directory
- **WHEN** a developer lists the contents of `frontend/src`
- **THEN** all eight folders are present

#### Scenario: Fresh clone
- **WHEN** a developer clones the repository and opens `frontend/src`
- **THEN** all eight folders exist without any manual creation step

### Requirement: Empty folders are tracked in version control
Each standard folder SHALL remain present in version control while it has no real files.

#### Scenario: Folder without real files
- **WHEN** a standard folder contains no source files yet
- **THEN** it contains a placeholder file so version control keeps the folder

### Requirement: Static media and icons are separated
The `assets` folder SHALL hold static media imported by the app (images), and the `icon` folder SHALL hold icon files and icon components.

#### Scenario: Adding an image
- **WHEN** a developer adds a logo or illustration
- **THEN** it is placed in `assets`

#### Scenario: Adding an icon
- **WHEN** a developer adds an icon
- **THEN** it is placed in `icon`, not in `assets`

### Requirement: Shared UI and logic have dedicated folders
The `components` folder SHALL hold UI pieces reused by more than one module or free of feature knowledge, `hooks` SHALL hold reusable custom hooks, and `utils` SHALL hold framework-independent helper functions.

#### Scenario: Component without feature knowledge
- **WHEN** a UI component has no knowledge of the chat feature
- **THEN** it is placed in `components`

#### Scenario: Pure helper function
- **WHEN** a helper does not depend on React or on any module
- **THEN** it is placed in `utils`

### Requirement: Features live under modules
The `modules` folder SHALL hold feature-scoped code grouped by feature, `layouts` SHALL hold page shells shared by several pages, and `routes` SHALL hold route definitions.

#### Scenario: New feature
- **WHEN** a developer builds a feature such as the chat page
- **THEN** its page, local components, types and local logic are grouped in one folder under `modules`
