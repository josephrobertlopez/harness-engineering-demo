# Exercise 2 — generalise, don't memorise

Brief: [lesson 3](../../lesson-03-generalise.md).

Write a skill at `skills/<your-skill-name>/SKILL.md` that passes **all
five** held-out tasks without containing any of their expected answers.

```bash
python tutorials/check.py 30-skill-authoring/02-generalise
```

The check does two things, and both must pass:

1. scores your skill on the held-out test split and requires 1.000;
2. searches every `.md` under `skills/` for the literal values those tasks
   expect. A perfect score with a memorised answer fails.

Worked examples that use *training* records are fine, and good practice.
State the rule (`<record_id>:<operation>`), not the answer.

`solution/` is the reference answer the test suite grades. Read it after
you have your own.
