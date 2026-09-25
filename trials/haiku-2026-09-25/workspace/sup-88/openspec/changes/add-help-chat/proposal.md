# Proposal: Help centre chatbot (SUP-88)

## Why

The support team receives approximately 40% of tier-1 support tickets on five recurring FAQ topics. A conversational terminal chatbot that answers these questions can deflect these tickets and reduce support workload.

This change implements the chatbot as specified in `prd.md`.

## What Changes

- **New chatbot CLI:** Terminal-based invocation via `python chatbot.py`
- **FAQ matching and answering:** Answers user questions that match FAQ topics using Claude API
- **Non-FAQ escalation:** Routes out-of-scope questions to support with a standard message
- **Safety filtering:** Detects and refuses card numbers (Luhn-validated) and passwords (pattern-based)
- **Session memory:** Maintains conversation context within a session (last 6 messages); no persistence across sessions
- **Claude integration:** Uses `claude-sonnet-5` model with specified API constraints

## Capabilities

### New Capabilities

- **FAQ-based question answering:** Terminal chatbot that answers customer questions from the FAQ using Claude
- **Out-of-FAQ escalation:** Automatically escalates questions outside the FAQ scope with a human-friendly message
- **Sensitive data protection:** Detects and refuses card numbers and passwords to prevent accidental exposure
- **Stateless sessions:** Each run is isolated; conversation history is not persisted

## Impact

- **Support:** Reduces tier-1 ticket volume by deflecting ~40% of FAQ-related inquiries to the chatbot
- **Security:** Prevents customers from accidentally sharing card numbers or passwords in the chat
- **User experience:** Provides immediate answers to common questions via terminal interface
- **Operations:** Stateless design simplifies deployment; no database or persistent storage required
