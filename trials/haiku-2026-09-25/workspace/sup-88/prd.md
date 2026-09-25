# PRD — Help centre chatbot (SUP-88)

## Problem

The support team receives approximately 40% of tier-1 support tickets on five recurring FAQ topics. A conversational chatbot that reliably answers these common questions can deflect these tickets and reduce support workload.

## Users

Customers accessing the help centre via terminal interface.

## Requirements

### PRD-1: Terminal interface and session management

The chatbot **MUST** be invoked via `python chatbot.py` and **SHALL** treat each invocation as a distinct session. Each session **MUST** end cleanly when the user signals end-of-input (Ctrl-D or Ctrl-Z). Sessions **MUST** be completely isolated from each other. The chatbot **MUST NOT** write any conversation data to persistent storage; all session data **MUST** be held only in memory and discarded when the session ends.

- WHEN a user runs `python chatbot.py` THEN a new interactive session begins
- WHEN a user enters Ctrl-D or Ctrl-Z THEN the session ends and all state is discarded
- WHEN the chatbot restarts THEN no memory of prior conversations exists
- WHEN a session ends THEN no data persists to disk or any persistent storage
- WHEN a new session begins THEN it has no access to any data from prior sessions

Source: interview.md Q1, Q5

### PRD-2: FAQ-related question handling

When a user asks a question matching a FAQ topic, the chatbot **SHALL** answer using the Claude API. The chatbot **MUST** answer only from the matched FAQ entry, not from general knowledge.

- WHEN a user asks a question that matches an FAQ entry THEN the chatbot invokes Claude to generate a response
- WHEN an FAQ-matched question is answered THEN the response is based exclusively on the matched FAQ entry

Source: interview.md Q2

### PRD-3: Out-of-FAQ escalation and turn marking

When a user asks a question that does not match any FAQ entry, the chatbot **MUST** respond with the exact escalation message and **MUST NOT** invoke Claude for that turn. Each such turn **SHALL** be internally marked as escalated (indicating to the chatbot that this turn bypassed the model). Uncovered (non-matching) questions **SHALL** produce the escalation response without any API call.

- WHEN a user asks a question outside the FAQ scope THEN the chatbot responds with exactly: `I don't know that one yet — I've passed your question to a human.`
- WHEN a question outside the FAQ is received THEN the turn is marked as escalated (internal flag only; no logging, metrics, or other observable side effects required)
- WHEN a question outside the FAQ is received THEN no Claude API call is made for that turn
- WHEN a question does not match any FAQ entry THEN the escalation message is returned immediately without invoking the model

Source: interview.md Q2, Q19

### PRD-4: Card number detection and refusal

The chatbot **MUST** detect and refuse messages containing valid card numbers within a single message. A valid card number is 13–19 digits, may contain spaces or dashes, and must pass the Luhn check. Card numbers are detected on a per-message basis; detection does not span across multiple messages in the conversation.

- WHEN a message contains a valid card number (13–19 digits with optional spaces/dashes, passing Luhn validation) THEN the chatbot responds with exactly: `I can't help with passwords or card numbers here. Please contact support@example.com.`
- WHEN a card number is detected THEN it is not stored in conversation memory
- WHEN a card number refusal occurs THEN the Claude API is not called for that turn
- WHEN a card number is split or distributed across multiple user messages THEN detection applies independently to each message

Source: interview.md Q4

### PRD-5: Password detection and refusal

The chatbot **MUST** detect and refuse messages containing passwords. A password is detected by the patterns "password is", "password:", or "pwd=" (case-insensitive matching) followed immediately or with single whitespace by a word containing at least one digit or symbol.

- WHEN a message contains a detected password (case-insensitive matching of "password is", "password:", or "pwd=" + word with digit/symbol) THEN the chatbot responds with exactly: `I can't help with passwords or card numbers here. Please contact support@example.com.`
- WHEN a password is detected THEN it is not stored in conversation memory
- WHEN a password refusal occurs THEN the Claude API is not called for that turn
- WHEN the password pattern is followed by multiple spaces or a newline before the word THEN detection still applies (pattern matching treats any whitespace as a delimiter)

Source: interview.md Q4

### PRD-6: Conversation context window

The chatbot **SHALL** maintain a sliding context window of the last 6 messages (three user-bot exchanges) within a session and **MUST** send this context to Claude with each question about an FAQ topic.

- WHEN a user asks a FAQ-related question THEN the last 6 messages from the current session are included in the Claude API call
- WHEN more than 6 messages accumulate in a session THEN messages older than 6 are dropped and not sent to Claude
- WHEN a session ends THEN all message history is discarded; a new session has no access to prior messages

Source: interview.md Q5

### PRD-7: Claude API specification

The chatbot **MUST** use the Claude API with the model `claude-sonnet-5` (exactly that identifier, with no date suffix) and **SHALL** set `max_tokens` to 512. The chatbot **MUST NOT** set the `temperature` parameter, as this model rejects it with a 400 error. The chatbot **MUST** read the API key from the environment variable `ANTHROPIC_API_KEY` and **MUST NOT** read it from source code or configuration files.

- WHEN invoking Claude THEN the model id must be exactly `claude-sonnet-5`
- WHEN invoking Claude THEN `max_tokens` must be set to 512
- WHEN invoking Claude THEN `temperature` must not be set
- WHEN the chatbot starts THEN it must read the API key from the `ANTHROPIC_API_KEY` environment variable
- WHEN the chatbot runs THEN the API key must not be present in source code or configuration files

Source: interview.md Q11, Q20

### PRD-8: Terminal-only implementation scope

This chatbot implementation **SHALL** be terminal-only via `python chatbot.py`. The web-based help centre widget is out of scope and assigned to a separate ticket.

- WHEN the chatbot is invoked THEN it runs in terminal mode only
- WHEN a user needs web access to the help centre THEN that capability is served by the separate web widget ticket, not this implementation

Source: interview.md Q1

## Non-goals

The following are explicitly not required and left to the developer's discretion:

- **FAQ matching mechanism** (Q6): The method for determining whether a user question matches an FAQ entry is not specified. The developer may use keyword matching, semantic similarity, or any other approach.
- **System prompt and Claude guidance** (Q7): The specific system prompt, instructions, or style guidance for Claude is not specified.
- **API error handling** (Q8): Behavior when the Claude API fails, times out, or returns an error is not specified.
- **AI attribution** (Q9): Whether the chatbot should identify itself as AI or mention Claude is not specified.
- **FAQ attribution in responses** (Q10): Whether answers should reference which FAQ section they come from is not specified.
- **FAQ context formatting** (Q12): How FAQ information (full text, entry only, keywords) is provided to Claude is not specified.
- **Message history formatting** (Q13): The format for sending the 6-message context to Claude (JSON with roles, plain text, etc.) is not specified.
- **Terminal interaction model** (Q14): Prompt symbols, line breaks, formatting, and other terminal UI details are not specified.
- **Testing and verification approach** (Q15): How to test the chatbot and verify it meets acceptance criteria is not specified.
- **Empty input handling** (Q16): Behavior when a user submits empty or whitespace-only input is not specified.
- **Escalated message counting** (Q17): Whether escalated turns (no-model calls) count toward the 6-message context window is not specified.
- **Conversation history display** (Q18): Whether to show prior user questions or only the bot's responses is not specified.
- **Escalation logging and metrics** (Q19): Whether escalated turns result in logging, metrics, alerts, or other observable side effects is not specified; only the escalation message and no-model-call behavior are required.
- **Success metrics** (Q3): Target accuracy or success rate for FAQ question answering is not specified; this is a non-goal.

## Open questions

None. All material decisions have been resolved or delegated as non-goals.
