# Lesson 3 — Generalise, don't memorise

## The failure that scores well

Here is a skill that gets a perfect score and is worthless:

```markdown
## Rules
- For REC-4843, the idempotency_key is `REC-4843:reconcile`.
- For REC-4803, the timestamp is `2026-03-07T06:30:12Z`.
- The amount for REC-4833 is 40.48.
```

It passes every test task. It also teaches nothing, helps with no record it
has not already seen, and will silently do nothing the first time it meets
real data.

This is not a hypothetical. It is the single most likely thing to happen
when you optimise against a visible score, and it is why the evolution loop
in this repo gates on a **held-out** split the proposer never sees.

## The test

Ask: **would this rule still be correct for an input I have never seen?**

| memorised | generalised |
|---|---|
| "For REC-4843, use `REC-4843:reconcile`" | "The idempotency key is `<record_id>:<operation>`" |
| "The amount for REC-4833 is 40.48" | "Round half-to-even at two decimals" |
| "Timestamp is 2026-03-07T06:30:12Z" | "ISO-8601, `T` separator, trailing Z" |

The right-hand column is shorter, which is usually the tell. A rule that
needs one line per case is not a rule, it is a lookup table with extra steps.

## What the real model produced

For comparison — this is what the Skill Proposer wrote unprompted during a
live run, after the Wiki Maintainer root-caused the failures:

```markdown
2. Idempotency key: `<record_id>:<operation>` -- colon separator, nothing else.
   - Do NOT append today's date, a timestamp, a counter, or a random suffix.
     Uniqueness is not your job; determinism is.
   - Example: record REC-4840, operation reconcile -> `REC-4840:reconcile`.
```

Note what it did: stated the rule, named the **specific wrong thing** it had
observed, and used a *training* record in the example — never one from the
split it was being scored on. The negative instruction ("do NOT append a
date") is doing as much work as the positive one, because that was the
actual observed failure.

## Exercise

Write a skill in
`exercises/02-generalise/skills/<your-name>/SKILL.md` that passes **all five**
test tasks *without* containing any expected answer as a literal.

```bash
python tutorials/check.py 30-skill-authoring/02-generalise
```

The check scores you on the held-out split **and** greps your skill for the
literal expected values. Both must pass. A perfect score with a memorised
answer fails — as it should.

---

Next: [Lesson 4 — Budgets and failure modes](lesson-04-failure-modes.md)
