# OpenSpec: Help centre chatbot (SUP-88)

## ADDED Requirements

### Requirement: Terminal interface and session management

The chatbot **MUST** be invoked via `python chatbot.py` and **SHALL** treat each invocation as a distinct session. Each session **MUST** end cleanly when the user signals end-of-input (Ctrl-D or Ctrl-Z). Sessions **MUST** be completely isolated from each other. The chatbot **MUST NOT** write any conversation data to persistent storage; all session data **MUST** be held only in memory and discarded when the session ends.

Trace: PRD-1

#### Scenario: Session starts cleanly

- **WHEN** a user runs `python chatbot.py`
- **THEN** a new interactive session begins, ready to accept user input

#### Scenario: Session ends on Ctrl-D

- **WHEN** a user enters Ctrl-D during a session
- **THEN** the session ends and all state is discarded

#### Scenario: Session ends on Ctrl-Z

- **WHEN** a user enters Ctrl-Z during a session
- **THEN** the session ends and all state is discarded

#### Scenario: Sessions are isolated

- **WHEN** a new session begins after a prior session ends
- **THEN** it has no access to any data from prior sessions

#### Scenario: No persistence to disk

- **WHEN** a session ends
- **THEN** no data persists to disk or any persistent storage

---

### Requirement: FAQ-related question handling

When a user asks a question matching a FAQ topic, the chatbot **SHALL** answer using the Claude API. The chatbot **MUST** answer only from the matched FAQ entry, not from general knowledge.

Trace: PRD-2

#### Scenario: FAQ-matched question invokes Claude

- **WHEN** a user asks a question that matches an FAQ entry
- **THEN** the chatbot invokes Claude to generate a response

#### Scenario: Response is based on matched FAQ entry

- **WHEN** an FAQ-matched question is answered
- **THEN** the response is based exclusively on the matched FAQ entry

---

### Requirement: Out-of-FAQ escalation and turn marking

When a user asks a question that does not match any FAQ entry, the chatbot **MUST** respond with the exact escalation message and **MUST NOT** invoke Claude for that turn. Each such turn **SHALL** be internally marked as escalated (indicating to the chatbot that this turn bypassed the model). Uncovered (non-matching) questions **SHALL** produce the escalation response without any API call.

Trace: PRD-3

#### Scenario: Non-FAQ question returns escalation message

- **WHEN** a user asks a question outside the FAQ scope
- **THEN** the chatbot responds with exactly: `I don't know that one yet — I've passed your question to a human.`

#### Scenario: Escalated turn is marked internally

- **WHEN** a question outside the FAQ is received
- **THEN** the turn is marked as escalated (internal flag only; no logging, metrics, or other observable side effects)

#### Scenario: No Claude API call for escalated turn

- **WHEN** a question outside the FAQ is received
- **THEN** no Claude API call is made for that turn

---

### Requirement: Card number detection and refusal

The chatbot **MUST** detect and refuse messages containing valid card numbers within a single message. A valid card number is 13–19 digits, may contain spaces or dashes, and must pass the Luhn check. Card numbers are detected on a per-message basis; detection does not span across multiple messages in the conversation.

Trace: PRD-4

#### Scenario: Card number is detected and refused

- **WHEN** a message contains a valid card number (13–19 digits with optional spaces/dashes, passing Luhn validation)
- **THEN** the chatbot responds with exactly: `I can't help with passwords or card numbers here. Please contact support@example.com.`

#### Scenario: Detected card numbers are not stored in memory

- **WHEN** a card number is detected
- **THEN** it is not stored in conversation memory

#### Scenario: Claude is not called for card number

- **WHEN** a card number refusal occurs
- **THEN** the Claude API is not called for that turn

#### Scenario: Card numbers with spaces and dashes are detected

- **WHEN** a message contains a card number with spaces or dashes (e.g., "4532 1234 5678 90" or "4532-1234-5678-90")
- **THEN** it is detected and the refusal message is returned

---

### Requirement: Password detection and refusal

The chatbot **MUST** detect and refuse messages containing passwords. A password is detected by the patterns "password is", "password:", or "pwd=" (case-insensitive matching) followed immediately or with single whitespace by a word containing at least one digit or symbol.

Trace: PRD-5

#### Scenario: Password is detected and refused

- **WHEN** a message contains a detected password (case-insensitive matching of "password is", "password:", or "pwd=" + word with digit/symbol)
- **THEN** the chatbot responds with exactly: `I can't help with passwords or card numbers here. Please contact support@example.com.`

#### Scenario: Detected passwords are not stored in memory

- **WHEN** a password is detected
- **THEN** it is not stored in conversation memory

#### Scenario: Claude is not called for password

- **WHEN** a password refusal occurs
- **THEN** the Claude API is not called for that turn

#### Scenario: Case-insensitive password pattern matching

- **WHEN** a message contains "Password is abc123" or "PASSWORD IS xyz789" or "password: 123pass"
- **THEN** it is detected and the refusal message is returned

#### Scenario: Whitespace variations in password pattern

- **WHEN** the password pattern is followed by multiple spaces or a newline before the word
- **THEN** detection still applies (pattern matching treats any whitespace as a delimiter)

---

### Requirement: Conversation context window

The chatbot **SHALL** maintain a sliding context window of the last 6 messages (three user-bot exchanges) within a session and **MUST** send this context to Claude with each question about an FAQ topic.

Trace: PRD-6

#### Scenario: Context includes last 6 messages

- **WHEN** a user asks a FAQ-related question
- **THEN** the last 6 messages from the current session are included in the Claude API call

#### Scenario: Older messages are dropped

- **WHEN** more than 6 messages accumulate in a session
- **THEN** messages older than 6 are dropped and not sent to Claude

#### Scenario: Context clears at session end

- **WHEN** a session ends
- **THEN** all message history is discarded; a new session has no access to prior messages

---

### Requirement: Claude API specification

The chatbot **MUST** use the Claude API with the model `claude-sonnet-5` (exactly that identifier, with no date suffix) and **SHALL** set `max_tokens` to 512. The chatbot **MUST NOT** set the `temperature` parameter, as this model rejects it with a 400 error. The chatbot **MUST** read the API key from the environment variable `ANTHROPIC_API_KEY` and **MUST NOT** read it from source code or configuration files.

Trace: PRD-7

#### Scenario: Model is exactly claude-sonnet-5

- **WHEN** invoking Claude
- **THEN** the model id must be exactly `claude-sonnet-5`

#### Scenario: max_tokens is set to 512

- **WHEN** invoking Claude
- **THEN** `max_tokens` must be set to 512

#### Scenario: temperature is not set

- **WHEN** invoking Claude
- **THEN** `temperature` must not be set

#### Scenario: API key is read from environment variable

- **WHEN** the chatbot starts
- **THEN** it must read the API key from the `ANTHROPIC_API_KEY` environment variable

#### Scenario: API key is not in source code

- **WHEN** the chatbot runs
- **THEN** the API key must not be present in source code or configuration files

---

### Requirement: Terminal-only implementation scope

This chatbot implementation **SHALL** be terminal-only via `python chatbot.py`. The web-based help centre widget is out of scope and assigned to a separate ticket.

Trace: PRD-8

#### Scenario: Chatbot runs in terminal mode only

- **WHEN** the chatbot is invoked
- **THEN** it runs in terminal mode only

#### Scenario: Web access is out of scope

- **WHEN** a user needs web access to the help centre
- **THEN** that capability is served by the separate web widget ticket, not this implementation
