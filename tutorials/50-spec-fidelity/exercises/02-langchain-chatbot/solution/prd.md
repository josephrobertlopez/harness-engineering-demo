# PRD — Help centre chatbot (SUP-88)

Source ticket: `ticket.md` (SUP-88). Each requirement cites the stakeholder
answer it came from.

## Problem

About 40% of tier-1 support tickets are one of five questions that already
have signed-off answers in `faq.md`. Customers wait hours for a human to
paste an answer that already exists. Support wants a chatbot that answers
those five, hands everything else to a human, and never becomes a place
where card numbers and passwords get sent to a third party.

## Users

- **Customers** asking a help-centre question.
- **Support agents**, who receive the escalated questions.

## Requirements

### PRD-1: Answer from the FAQ only

The bot SHALL select the `faq.md` entry whose keywords best match the
question and MUST instruct the model to answer from that entry alone.

- WHEN a customer asks "I forgot my login, how do I reset it?" THEN the
  model receives the password-reset entry and the bot returns the model's
  reply.

Source: stakeholder-answers.md Q1.

### PRD-2: Escalate what the FAQ does not cover

When no FAQ entry matches, the bot SHALL reply exactly
`I don't know that one yet — I've passed your question to a human.`, mark
the turn escalated, and make no model call for that turn.

- WHEN a customer asks about the office dog THEN the reply is the
  escalation text, the turn is escalated, and the model is not called.

Source: stakeholder-answers.md Q2.

### PRD-3: Conversation memory

The bot SHALL send the last 6 messages of the current session (three
exchanges) with each new question and MUST drop older ones. Sessions MUST
be isolated from each other. Memory MUST NOT be written to disk.

- WHEN a customer asks a follow-up THEN the model receives the previous
  exchange.
- WHEN a session has 5 exchanges THEN the model receives only the last 6
  messages plus the new question.
- WHEN two sessions are active THEN neither sees the other's messages.

Source: stakeholder-answers.md Q3.

### PRD-4: Refuse card numbers and passwords

A message containing a card number (13–19 digits, spaces or dashes
allowed, passing the Luhn check) or a shared password ("password is",
"password:" or "pwd=" followed by one word containing a digit or symbol)
SHALL be refused before any model call with exactly
`I can't help with passwords or card numbers here. Please contact support@example.com.`
The refused message MUST NOT be kept in memory.

- WHEN a message contains `4111 1111 1111 1111` THEN the reply is the
  refusal and the model is not called.
- WHEN a message says "my password is hunter22" THEN the reply is the
  refusal.
- WHEN the next question is asked THEN the refused message is not in the
  history sent to the model.
- WHEN a message quotes order number `1234-5678-9012-3456` (fails Luhn)
  THEN it is not refused.
- WHEN a message says "my password is not working" THEN it is not refused.

Source: stakeholder-answers.md Q4.

### PRD-5: Model configuration

The bot SHALL use `ChatAnthropic` with model `claude-sonnet-5` and
`max_tokens` 512, and MUST NOT set `temperature` (the API returns 400 for it
on this model). The API key MUST come from the environment.

- WHEN the model is constructed THEN its parameters are exactly
  `model="claude-sonnet-5"` and `max_tokens=512`, with no temperature.

Source: stakeholder-answers.md Q5.

### PRD-6: Terminal chat

The bot SHALL run as `python chatbot.py`: one session per run, reading
questions from standard input and ending cleanly on end-of-input.

- WHEN standard input closes THEN the program exits with status 0.

Source: stakeholder-answers.md Q6.

## Non-goals

- Web UI, streaming, persistence across restarts (Q3, Q6, Q7).
- Embeddings or a vector store — five entries do not need one (Q7).
- Languages other than English (Q7).
- Answering anything outside `faq.md` (Q1).

## Open questions

None open. Resolved during review:

- "Remember stuff" → PRD-3 (six messages, per session, in memory).
- "Not say anything bad" → PRD-4 (card numbers and passwords, refused
  before the model sees them), plus PRD-1 grounding.
- "Smart about what it doesn't know" → PRD-2.
