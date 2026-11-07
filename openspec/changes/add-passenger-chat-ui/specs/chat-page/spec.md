# Spec Delta

## Purpose

Defines the chat screen as a whole: how it is laid out, which states it shows (loading, error, empty, populated) and how it keeps the latest message in view.

## ADDED Requirements

### Requirement: Chat page layout
The chat page SHALL show the conversation inside a single bordered container that fills the available height, with the messages area above and the composer pinned below it.

#### Scenario: Opening the chat page
- **WHEN** a user opens the chat page
- **THEN** one bordered container is shown with the messages area on top and the composer at the bottom

#### Scenario: Long conversation
- **WHEN** the messages do not fit in the available height
- **THEN** only the messages area scrolls and the composer stays visible

### Requirement: Page spacing adapts to screen width
The chat page SHALL use smaller outer and inner padding on narrow screens than on wide screens.

#### Scenario: Phone width
- **WHEN** the viewport is narrower than the medium breakpoint
- **THEN** the page and the messages area use the compact padding

#### Scenario: Desktop width
- **WHEN** the viewport is at or above the medium breakpoint
- **THEN** the page and the messages area use the wider padding

### Requirement: Empty conversation shows a welcome message
When the conversation has no messages, the messages area SHALL show an assistant welcome message introducing the Nubara flight assistant and inviting the passenger to ask about their flight change.

#### Scenario: Conversation without messages
- **WHEN** the conversation contains no messages and is not loading
- **THEN** the welcome message is displayed with the assistant avatar

#### Scenario: First message sent
- **WHEN** the first message is added to the conversation
- **THEN** the welcome message is no longer shown

### Requirement: Loading state
While the conversation is loading, the messages area SHALL show the text "Loading conversation..." centered, instead of messages or the welcome message.

#### Scenario: Conversation loading
- **WHEN** the page is told the conversation is loading
- **THEN** the loading text is shown centered in the messages area and no messages are shown

### Requirement: Error banner
The chat page SHALL show an error banner above the conversation container when an error message is provided, and no banner otherwise.

#### Scenario: Error present
- **WHEN** an error message is provided to the page
- **THEN** a banner with that message is displayed above the container

#### Scenario: No error
- **WHEN** no error message is provided
- **THEN** no banner is displayed and no space is reserved for it

### Requirement: Latest message stays in view
The chat page SHALL scroll the messages area so the newest message is visible: instantly when messages are first displayed, and smoothly when a new message is added.

#### Scenario: Opening a conversation with messages
- **WHEN** messages are displayed for the first time
- **THEN** the messages area is positioned at the last message without animation

#### Scenario: New message added
- **WHEN** a message is appended to the conversation
- **THEN** the messages area scrolls smoothly until that message is visible

### Requirement: Page does not depend on a backend
The chat page SHALL render and respond to input using only the data and callbacks it is given, and SHALL NOT send requests to a backend itself.

#### Scenario: Opening the page with no backend available
- **WHEN** the chat page is opened and no backend is running
- **THEN** it renders completely and no backend request is attempted
