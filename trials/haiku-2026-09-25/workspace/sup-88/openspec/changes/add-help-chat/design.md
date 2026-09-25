# Design: Help centre chatbot (SUP-88)

## Technical Approach

The chatbot is a stateless, terminal-based Python CLI that reads user questions from stdin and returns answers from the FAQ via the Claude API.

**Architecture:**
- **Input:** Terminal, line-by-line user input via stdin; session ends on Ctrl-D or Ctrl-Z
- **Processing pipeline:**
  1. Accept user input from terminal
  2. Detect and refuse sensitive data (card numbers via Luhn check, passwords via pattern)
  3. Determine if question matches an FAQ entry (mechanism: non-goal, delegated to developer)
  4. If matched: call Claude with FAQ entry and conversation context, return response
  5. If not matched: return exact escalation message, do not call Claude
- **Output:** Response sent to stdout; marked as escalated if non-FAQ
- **Context:** Maintain in-memory sliding window of last 6 messages (3 exchanges) per session
- **Persistence:** None; all state is discarded when session ends

**Dependencies:**
- Claude API (`claude-sonnet-5` model)
- Python 3.x
- Anthropic SDK for Python
- API key from `ANTHROPIC_API_KEY` environment variable

## Architecture Decisions

### Decision: Session-based, stateless design

**Reason:** Keeps the implementation simple and deployment straightforward. No database, no file I/O, no cross-session state to manage. Each invocation is independent, so the chatbot can be horizontally scaled if needed without session synchronization.

### Decision: 6-message context window

**Reason:** Balances context length for coherent multi-turn conversations with token economy. Three user-bot exchanges provide enough context for follow-up questions without inflating Claude API costs or hitting token limits.

### Decision: In-memory only, no persistence

**Reason:** Simplifies data handling and avoids compliance complications with storing customer support conversations. Sessions are ephemeral; users who need to resume a conversation can start a new session and re-state their context.

### Decision: Exact escalation and refusal messages

**Reason:** Ensures consistent, branded messaging to users. Exact strings prevent support team from being surprised by what customers see, and make testing deterministic.

### Decision: API key from environment variable

**Reason:** Follows the principle of secrets management; API keys should never be in source code or config files. Allows the chatbot to run in different environments (dev, staging, prod) with different API keys without code changes.

## File Changes

No existing files are modified. New files created:

- `chatbot.py` — Main CLI entry point
- `requirements.txt` — Python dependencies (anthropic SDK, etc.)
- `faq.py` — FAQ data structure and matching logic
- `safety.py` — Card number and password detection
- `session.py` — Session state and context window management
- `tests/` — Test suite (test scenarios from spec)

## Data and Scale Assumptions

- **FAQ size:** 5 entries (provided in `faq.md`)
- **Session size:** Up to ~6 messages per session in memory; older messages dropped
- **Claude context:** Last 6 messages + FAQ entry + system prompt, typically < 1000 tokens
- **Latency:** Claude API response time (typically 1-3 seconds); no additional performance constraints
- **Concurrency:** Each invocation is a separate process; no concurrent sessions within a single process
