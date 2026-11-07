# Spec Delta

## Purpose

Defines the shared look of the passenger application: light and dark color schemes that follow the system, the typography and the surface styling every screen builds on.

## ADDED Requirements

### Requirement: Color scheme follows the system preference
The application SHALL use the dark palette when the operating system prefers a dark color scheme and the light palette otherwise, and SHALL switch when that preference changes while the app is open.

#### Scenario: System prefers dark
- **WHEN** the app loads and the system color scheme is dark
- **THEN** the page, containers and text use the dark palette

#### Scenario: System prefers light
- **WHEN** the app loads and the system color scheme is light
- **THEN** the page, containers and text use the light palette

#### Scenario: Preference changes while open
- **WHEN** the system color scheme changes while the app is open
- **THEN** the app switches palette without a reload

### Requirement: Readable text in both palettes
In both palettes, primary text, muted text and status colors SHALL stay legible on the page background and on container surfaces.

#### Scenario: Reviewing both palettes
- **WHEN** the chat page with a decision card is displayed in the light palette and then in the dark palette
- **THEN** message text, the composer placeholder, labels and status chips are all readable against their backgrounds

### Requirement: Typography
Body text SHALL use Inter and headings SHALL use Manrope, both served from the application itself, and references such as booking, case and policy identifiers SHALL use a monospace font. Each SHALL fall back to a system font when unavailable.

#### Scenario: Fonts load without a third party
- **WHEN** the application is opened
- **THEN** its fonts are requested only from the application's own origin

#### Scenario: Fonts unavailable
- **WHEN** the web fonts fail to load
- **THEN** text is still displayed using system fonts with no layout break

### Requirement: Layered surfaces
The page background SHALL differ from the surface of containers, and containers SHALL have a thin visible border. In the light palette they MAY have a soft shadow, and in the dark palette they SHALL have none.

#### Scenario: Container on the page
- **WHEN** the chat container is displayed
- **THEN** it is distinguishable from the page background by color and a 1px border

#### Scenario: Dark palette container
- **WHEN** the dark palette is active
- **THEN** the container shows no shadow
