# Design: Help centre chatbot

## Technical Approach

Two modules with a hard line between them.

- `policy.py` is stdlib only: FAQ loading, keyword retrieval, the
  sensitive-data check, the memory window, the fixed replies and the model
  parameters. Every decision the PRD makes lives here, testable with no
  LangChain installed.
- `chatbot.py` is the LangChain wiring: a `ChatPromptTemplate` with a
  `MessagesPlaceholder` for history, piped into the chat model and a
  `StrOutputParser`, with an `InMemoryChatMessageHistory` per session.

## Architecture Decisions

### Decision: keyword retrieval, not embeddings

Five FAQ entries. Each carries a `keywords:` line; the entry with the most
keyword hits wins, ties go to the first. Deterministic, explainable, and a
miss is a clean escalation rather than a low-confidence guess. Embeddings
are a non-goal (PRD).

### Decision: guard before the chain, not inside the prompt

A prompt line saying "ignore card numbers" still sends the card number to a
third party. The check runs before the chain is invoked, and a refused
message never reaches the history object.

### Decision: the model is injected

`HelpBot(model=...)` takes any LangChain chat model. Production passes
`ChatAnthropic`; tests pass `FakeListChatModel` behind a recorder, so the
tests can assert exactly which messages the model would have received.

## Data Flow

question → sensitive? → refuse | retrieve FAQ entry → none? → escalate |
prompt(system + entry, last 6 messages, question) → model → reply →
append (question, reply) to the session's history.

## File Changes

- `impl/policy.py` (new)
- `impl/chatbot.py` (new)
- `impl/faq.md` (copied from the ticket attachment)
- `impl/tests/test_policy.py`, `impl/tests/test_chatbot.py` (new)
