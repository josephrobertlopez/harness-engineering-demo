# Exercise 1 — your first skill

Brief: [lesson 2](../../lesson-02-first-skill.md).

Write one skill at `skills/<your-skill-name>/SKILL.md` in this folder. The
check scores the no-skills baseline and your skill on the held-out test
split, and passes when your skill makes **at least two more tasks** pass.

```bash
python tutorials/check.py 30-skill-authoring/01-first-skill
```

When it fails it prints the baseline, your score, and how many tasks you
gained. The eval command in lesson 2 names each remaining failure and the
exact value the task expected.

`solution/` is the reference answer the test suite grades to prove the
exercise is solvable. Read it after you have a passing skill of your own.
