# Exercise 2 — Specificity

Two vague rules. Rewrite each so an agent could act on it without guessing.

> **Rule A (vague):** "Handle dates properly."
>
> **Rule B (vague):** "Round money the right way."

Write your rewrites into `rules/instructions/SKILL.md` in this folder, using
the skill format from [Track 30](../../../30-skill-authoring/lesson-01-anatomy.md):

```markdown
---
name: instructions
description: ...
---

1. <your rewrite of Rule A>
2. <your rewrite of Rule B>
```

Then: `python tutorials/check.py 00-prompting/02-specificity`

The check runs your rewrites against the benchmark. If the agent can act on
them, the `iso_z` and `round_even` tasks pass. If your rewrite names the
topic rather than the transformation, they will not.

You are not being graded on prose style — you are being graded on whether
the instruction contains enough information to follow.
