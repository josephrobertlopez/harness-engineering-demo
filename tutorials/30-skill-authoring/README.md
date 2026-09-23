# Track 30 — Skill authoring

**~45 minutes. Offline, no API key.**

Most advice about writing skills is unfalsifiable. This track is not: you
write a skill, run one command, and get a number. Then you change it and get
a different number.

## Prerequisites

- Python 3.12+
- You have run `python -m unittest discover -s tests -t .` from the repo root
  and it passed. That is the whole setup.

## What you will end up with

A skill you wrote, scored against a held-out split the skill never saw, and
compared against the no-skills baseline — so you can say "this helped" and
mean it.

## Lessons

| # | Lesson | Time |
|---|---|---|
| 1 | [Anatomy of a skill](lesson-01-anatomy.md) — and the one thing a skill is *for* | 10 min |
| 2 | [Your first skill](lesson-02-first-skill.md) — write it, measure it | 15 min |
| 3 | [Generalise, don't memorise](lesson-03-generalise.md) — the failure that scores well and teaches nothing | 15 min |
| 4 | [Budgets and failure modes](lesson-04-failure-modes.md) — why good skills get rejected | 5 min |

## Checking your work

```bash
# Check one exercise
python tutorials/check.py 30-skill-authoring/01-first-skill

# Check the whole track
python tutorials/check.py 30-skill-authoring
```

## The honest caveat, up front

These exercises grade against a **simulated** agent. It recognises that your
skill states a rule by matching keywords, which is a stand-in for
understanding it. That is enough to tell a specific instruction from a vague
one, and it is why the exercises work with no API key — but it cannot tell a
well-written skill from a merely correct one.

Against a real model, phrasing matters in ways nothing here measures. Treat
the score as a floor: failing it means the skill is definitely unclear;
passing it does not mean the skill is good.
