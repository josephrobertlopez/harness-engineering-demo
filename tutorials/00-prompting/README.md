# Track 00 — Prompting, measured

**~50 minutes. Offline, no API key.**

Most prompting advice is a list of tips you cannot check. This track gives
you two things that make it an engineering activity instead: a **vocabulary**
for saying precisely why an output was bad, and a **harness** that turns
"I think this is better" into a number.

## Prerequisites

- Python 3.12+, and `python -m unittest discover -s tests -t .` passes.
- Nothing else. No API key.

## Why this track exists

The repo you are standing in already measured something worth knowing.
Haiku 4.5, running a five-family benchmark with no help:

- It **passed** every quirk the environment told it about — it read an error
  message and retried with the right id; it saw a `more_pages` flag and
  paginated.
- It **failed** every silent convention — output timestamp format, rounding
  mode, key separator.

So: **prompting buys you nothing where the model can already discover the
answer, and everything where it cannot.** Most prompt bloat is spent on the
first category. Knowing which one you are in is the skill.

## Lessons

| # | Lesson | Time |
|---|---|---|
| 1 | [What prompting can and cannot fix](lesson-01-what-prompting-fixes.md) | 10 min |
| 2 | [Scoring an output on five dimensions](lesson-02-scoring.md) | 15 min |
| 3 | [The seven anti-patterns](lesson-03-anti-patterns.md) | 15 min |
| 4 | [Specificity, measured](lesson-04-specificity.md) | 10 min |

## Checking your work

```bash
python tutorials/check.py 00-prompting
```

## Where the vocabulary comes from

Lessons 2 and 3 teach two tools I have found worth the effort: a
**five-dimension rubric** for saying precisely why an output is bad, and a
list of **seven recurring failure patterns** for saying why the model
produced it.

Neither is novel and neither needs buying into. They are here because a
shared vocabulary is what turns "this feels off" into a change someone can
actually make — and because both are small enough to remember.
