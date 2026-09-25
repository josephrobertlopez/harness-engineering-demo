# What the support lead said when asked

You get these answers **only by asking**. They are written down so every
learner gets the same ones and the judge can check your PRD against them.
Ask the Interrogator persona (`personas/spec-interrogator.persona.md`) to
lead you there; notice which questions you would not have thought of.

**Q1. "Answer customer questions" — which questions?**
Only the five in `faq.md`. The bot finds the matching FAQ entry and the
model answers **from that entry only**. It must not improvise policy — a
made-up refund window is worse than no answer.

**Q2. "Smart about what it doesn't know" — what happens then?**
If no FAQ entry matches, the bot replies with exactly
`I don't know that one yet — I've passed your question to a human.` and
marks the turn as **escalated**. It does **not** call the model for that
turn; there is nothing for the model to ground on.

**Q3. "Remember stuff" — how much, for how long?**
Per session: the **last 6 messages** (three exchanges) go to the model with
each new question; older ones are dropped. Sessions are isolated from each
other. Nothing is written to disk — a restart forgets, and that is fine.

**Q4. "Not say anything bad" — what are you actually worried about?**
Customers paste **card numbers** and **passwords** into chat. A message
containing either is refused **before any model call** with exactly
`I can't help with passwords or card numbers here. Please contact support@example.com.`
and the refused message is **not kept in memory** — otherwise it would be
sent to the model on the next turn anyway.

But do not refuse the most common question we get. Concretely:

- a **card number** is 13–19 digits (spaces or dashes allowed between them)
  that **passes the Luhn check**. Order numbers are 16 digits too, and they
  fail Luhn; customers quote them all the time.
- a **shared password** is "password is", "password:" or "pwd=" followed by
  a single word containing a **digit or a symbol** — "my password is
  hunter22". "My password is not working" and "my password is expired" are
  questions, not passwords.

**Q5. "Use Claude" — which model, which settings?**
`ChatAnthropic` from `langchain-anthropic`, model **`claude-sonnet-5`**
(exactly that id, no date suffix), `max_tokens` **512**. Do **not** set
`temperature`: the API rejects it for this model with a 400. The API key
comes from the environment (`ANTHROPIC_API_KEY`), never from source.

**Q6. "Easy to try out" — how?**
A terminal chat: `python chatbot.py`, one session per run, ends cleanly on
end-of-input (Ctrl-D / Ctrl-Z). The web widget is a different ticket.

**Q7. Out of scope?**
Web UI, streaming, persistence, embeddings or a vector store, languages
other than English, and answering anything outside the FAQ.
