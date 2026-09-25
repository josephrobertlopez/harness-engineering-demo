## Why

About 40% of tier-1 tickets ask one of five questions that already have
signed-off answers. A chatbot grounded on that FAQ can answer them in
seconds, escalate the rest, and keep card numbers and passwords away from
the model. Traces to `prd.md` (SUP-88).

## What Changes

- Add a LangChain chatbot that answers only from the matching `faq.md`
  entry, using `ChatAnthropic` (`claude-sonnet-5`, `max_tokens=512`).
- Escalate unmatched questions with a fixed reply and no model call.
- Keep a six-message memory window per session, in memory only.
- Refuse card numbers and shared passwords before any model call, and keep
  them out of memory.
- Provide a terminal chat, `python chatbot.py`.

## Capabilities

### New Capabilities

- `help-chat`: grounded FAQ answers, escalation, memory, and sensitive-data
  refusal.

### Modified Capabilities

None.

## Impact

New code: `impl/policy.py` (stdlib), `impl/chatbot.py` (LangChain).
Dependencies: `langchain-core`, `langchain-anthropic`.
