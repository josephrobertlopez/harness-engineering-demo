---
description: Step 1 - interrogate ticket.md before anything is designed (you answer as the product owner)
argument-hint: "[your answers to the last batch of questions]"
---

Read `personas/spec-interrogator.persona.md` and act as that persona for this
whole command.

`ticket.md` is a Jira ticket assigned to me. `interview.md` (create it if it
does not exist) is the append-only record of what the product owner has
said so far. I am the product owner.

1. If `$ARGUMENTS` is not empty, those are my answers to your previous
   batch. Append them to `interview.md` under the questions they answer,
   in my words. Never rewrite or delete anything already in the file.
2. Read `ticket.md` and `interview.md`. List every assumption the ticket
   makes that the interview has not yet resolved: success criteria first,
   then constraints (performance, security, platform, dependencies), then
   edge cases and error behaviour, then what is explicitly out of scope.
3. Append your next batch of **at most five** questions to `interview.md`
   as `### Q<n>. <question>` with an empty `A:` line, and show them to me.
   Number questions continuously across batches.
4. If nothing material is left unresolved, say `INTERVIEW COMPLETE` and
   summarise the decisions in five lines or fewer.

Rules:
- Answer nothing yourself. Do not guess what the product owner would say.
- Do not read any file other than `ticket.md`, `interview.md`, `faq.md` (if
  present) and the persona.
- Ask about behaviour and constraints, not implementation. "What should
  happen when the amount is negative?", not "Should I use Flask?".
- A question the product owner answers with "no decision" becomes a
  non-goal. Record it as such; do not ask it again.
