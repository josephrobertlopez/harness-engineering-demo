## ADDED Requirements

### Requirement: Grounded FAQ answers

The bot SHALL select the `faq.md` entry whose keywords best match the
question and MUST pass that entry, and only that entry, to the model as the
source for its answer.

Trace: PRD-1

#### Scenario: Question covered by the FAQ

- **WHEN** a customer asks "I forgot my login, how do I reset it?"
- **THEN** the system message sent to the model contains the password-reset entry
- **AND** does not contain any other entry
- **AND** the bot returns the model's reply, not escalated

#### Scenario: Most keyword hits wins

- **WHEN** a question matches keywords from two entries
- **THEN** the entry with more keyword hits is selected

### Requirement: Escalation of uncovered questions

When no FAQ entry matches, the bot SHALL reply exactly
`I don't know that one yet — I've passed your question to a human.`, mark the
turn escalated, and MUST NOT call the model.

Trace: PRD-2

#### Scenario: Question not covered

- **WHEN** a customer asks "what is the office dog called?"
- **THEN** the reply is the escalation text and the turn is escalated
- **AND** the model is not called

### Requirement: Session memory window

The bot SHALL send the last 6 messages of the current session with each
question, MUST drop older messages, and MUST keep sessions isolated. Memory
is held in process only.

Trace: PRD-3

#### Scenario: Follow-up sees the previous exchange

- **WHEN** a customer asks a follow-up in the same session
- **THEN** the model receives the previous question and answer before the new question

#### Scenario: Only the last six messages are sent

- **GIVEN** a session with five completed exchanges
- **WHEN** the customer asks another question
- **THEN** the model receives exactly the last 6 history messages plus the new question

#### Scenario: Sessions are isolated

- **WHEN** two sessions each ask a question
- **THEN** neither session's history contains the other's messages

### Requirement: Sensitive data refusal

A message containing a card number (13 to 19 digits, optionally separated by
spaces or dashes) or a shared password SHALL be refused, before any model
call, with exactly
`I can't help with passwords or card numbers here. Please contact support@example.com.`
The refused message MUST NOT be stored in the session's history.

Trace: PRD-4

#### Scenario: Card number refused

- **WHEN** a message contains `4111 1111 1111 1111`
- **THEN** the reply is the refusal text and the model is not called

#### Scenario: Shared password refused

- **WHEN** a message says "my password is hunter22"
- **THEN** the reply is the refusal text

#### Scenario: Asking about passwords is not refused

- **WHEN** a message says "I forgot my password"
- **THEN** it is not refused

#### Scenario: Refused message is not remembered

- **GIVEN** a refused message in a session
- **WHEN** the customer asks a covered question
- **THEN** the history sent to the model does not contain the refused message

### Requirement: Model configuration

The bot SHALL construct `ChatAnthropic` with `model="claude-sonnet-5"` and
`max_tokens=512`, and MUST NOT pass `temperature` or an API key.

Trace: PRD-5

#### Scenario: Model parameters

- **WHEN** the model parameters are built
- **THEN** they are exactly `{"model": "claude-sonnet-5", "max_tokens": 512}`

### Requirement: Terminal chat

The bot SHALL run as `python chatbot.py`, one session per run, reading
questions from standard input and exiting with status 0 at end-of-input.

Trace: PRD-6

#### Scenario: End of input exits cleanly

- **WHEN** standard input closes
- **THEN** the chat loop returns 0
