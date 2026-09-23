# Lesson 4 — Specificity, measured

The claim "be specific" is itself unspecific. This lesson makes it checkable.

## The experiment

Three instructions for the same rule, in increasing specificity:

| | Instruction |
|---|---|
| A | Handle dates properly. |
| B | Format timestamps consistently for the downstream consumer. |
| C | Timestamps are ISO-8601: replace the space with `T` and append a trailing Z. `2026-03-04 11:02:33` becomes `2026-03-04T11:02:33Z`. |

A and B are the kind of thing that feels like guidance and is not. Neither
tells the agent anything it could act on — they name the *topic*, not the
*rule*. Only C contains information the agent did not already have.

Run all three through the harness and you get three numbers, not three
opinions.

## The three tests a rule must pass

1. **Does it name the transformation?** Not the topic. "Handle dates" names
   a topic; "append a trailing Z" names a transformation.
2. **Could a reader apply it to an input you did not show them?** If it only
   works for your example, it is a lookup table.
3. **Does it say what *not* to do, where you have seen it go wrong?** The
   real Skill Proposer wrote *"Do NOT append today's date, a timestamp, a
   counter, or a random suffix"* — because that was the observed failure.
   Negative instructions are cheap and disproportionately effective.

## Exercise

Two exercises for this track:

**`01-diagnose`** — classify three bad outputs by anti-pattern and by the
rubric dimension they damage. Vocabulary before technique.

**`02-specificity`** — you are given two vague rules. Rewrite them so an
agent can act on them, and the harness will tell you whether it could.

```bash
python tutorials/check.py 00-prompting
```

## The habit worth keeping

Measure, change **one thing**, measure again. Changing three things and
seeing the number rise teaches you nothing about which of the three
mattered — and one of them may have made it worse.

This is the same loop the evolution harness runs automatically: one atomic
proposal per iteration, gated on a held-out split, rejected if it does not
strictly improve. You are doing manually what
[Track 40](../40-harness/README.md) automates.

---

Back to [the track index](README.md), or on to
[Track 30 — skill authoring](../30-skill-authoring/README.md).
