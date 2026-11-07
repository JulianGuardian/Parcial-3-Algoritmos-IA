# Spec Delta

## Purpose

Defines how conversation messages look and behave: author alignment, bubble styling, width on different screens, and the guarantee that message text is shown as plain text.

## ADDED Requirements

### Requirement: Messages are aligned by author
Each message SHALL be shown with an avatar. User messages SHALL be aligned to the right and assistant messages to the left, in chronological order.

#### Scenario: Mixed conversation
- **WHEN** a conversation has a user message followed by an assistant message
- **THEN** the user message appears right-aligned above the left-aligned assistant message

#### Scenario: System message
- **WHEN** a message has the system role
- **THEN** it is shown like an assistant message

### Requirement: Author bubbles are visually distinct
User bubbles SHALL use the primary color as background with contrasting text, and assistant bubbles SHALL use the surface color with a border and the normal text color.

#### Scenario: Comparing two bubbles
- **WHEN** a user bubble and an assistant bubble are displayed
- **THEN** the user bubble has a primary background with contrasting text and the assistant bubble has a bordered surface background

### Requirement: Bubble width adapts to screen width
A message column SHALL be at most 78% of the messages area on wide screens and use the full width on narrow screens.

#### Scenario: Long message on desktop
- **WHEN** a long message is shown at or above the medium breakpoint
- **THEN** its bubble does not exceed 78% of the row width

#### Scenario: Long message on a phone
- **WHEN** a long message is shown below the medium breakpoint
- **THEN** its bubble may use the full row width

### Requirement: Message text is plain text
Message text SHALL be displayed exactly as received, with line breaks preserved. Markup, HTML and links inside the text SHALL NOT be interpreted.

#### Scenario: Text with line breaks
- **WHEN** a message contains two lines separated by a line break
- **THEN** both lines are shown on separate lines in the same bubble

#### Scenario: Text containing HTML
- **WHEN** a message contains `<b>Hello</b>` or `<img src=x onerror=alert(1)>`
- **THEN** the characters are shown literally and nothing is rendered or executed

### Requirement: Assistant messages can carry a decision card
An assistant message that has a disruption decision SHALL show its text bubble first and the decision card below it, aligned with the bubble. A message without a decision SHALL show no card.

#### Scenario: Message with a decision
- **WHEN** an assistant message has text and a decision
- **THEN** the text bubble is shown above the decision card

#### Scenario: Message without a decision
- **WHEN** an assistant message has no decision
- **THEN** only the text bubble is shown
