# Spec Delta

## Purpose

Defines the message composer at the bottom of the chat: typing and sending a question, the length limit, and suggested questions that help the passenger start.

## ADDED Requirements

### Requirement: Composer input
The composer SHALL provide a multiline text input with the placeholder "Ask about your flight change..." that grows up to six lines and then scrolls.

#### Scenario: Empty composer
- **WHEN** the composer is shown with no text
- **THEN** the placeholder is visible in the input

#### Scenario: Long input
- **WHEN** the user types more than six lines
- **THEN** the input stops growing and scrolls internally

### Requirement: Sending a message
The composer SHALL send the trimmed text when the user presses the send button or presses Enter, and SHALL insert a line break instead when the user presses Shift+Enter.

#### Scenario: Send with the button
- **WHEN** the input contains "  What are my options?  " and the user clicks the send button
- **THEN** the submit callback is called once with "What are my options?"

#### Scenario: Send with Enter
- **WHEN** the input contains text and the user presses Enter
- **THEN** the text is submitted and no line break is added

#### Scenario: New line with Shift+Enter
- **WHEN** the user presses Shift+Enter in the input
- **THEN** a line break is inserted and nothing is submitted

#### Scenario: Enter that confirms a text composition
- **WHEN** the user presses Enter only to confirm an in-progress input-method composition (for example an accented character)
- **THEN** the text is not submitted

### Requirement: Empty messages cannot be sent
The send button SHALL be disabled, and Enter SHALL do nothing, while the input contains only whitespace.

#### Scenario: Blank input
- **WHEN** the input is empty or only spaces
- **THEN** the send button is disabled and pressing Enter does not call the submit callback

### Requirement: Length limit
The composer SHALL NOT accept more than 500 characters, the limit of the backend question, and SHALL show a character counter once the text reaches 400 characters.

#### Scenario: Typing past the limit
- **WHEN** the input already holds 500 characters and the user types another one
- **THEN** the input still holds 500 characters

#### Scenario: Counter appears near the limit
- **WHEN** the input holds 400 or more characters
- **THEN** a counter such as "400/500" is shown, and it is not shown below 400

#### Scenario: Pasting a long text
- **WHEN** the user pastes 700 characters
- **THEN** only the first 500 are kept

### Requirement: Composer resets after sending
After a message is submitted, the composer SHALL clear the input.

#### Scenario: Submit clears the input
- **WHEN** a message is submitted
- **THEN** the input is empty and the counter is hidden

### Requirement: Disabled composer
While the composer is disabled, the input, the send button and the suggested questions SHALL not accept interaction.

#### Scenario: Waiting for a reply
- **WHEN** the composer is told it is disabled
- **THEN** the input cannot be edited, the send button is disabled and the suggestions cannot be clicked

### Requirement: Suggested questions
The composer SHALL offer the suggestions "What happened to my flight?", "What are my options?" and "Can I ask for compensation?". Choosing one SHALL put its text in the input and focus it, without sending it.

#### Scenario: Choosing a suggestion
- **WHEN** the user clicks "What are my options?" with an empty input
- **THEN** the input contains "What are my options?", has focus, and nothing is submitted

#### Scenario: Suggestion with existing text
- **WHEN** the input already contains text and the user clicks a suggestion
- **THEN** the input contains the suggestion text instead of the previous text

### Requirement: Accessible names
The input SHALL have an accessible name and the send button SHALL be labeled "Send message".

#### Scenario: Querying by role
- **WHEN** assistive technology or a test looks up the input and the button
- **THEN** the input is found by its accessible name and the button by the label "Send message"
