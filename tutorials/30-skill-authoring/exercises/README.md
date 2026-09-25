# Track 30 exercises

Two graded exercises for [track 30](../README.md). The briefs live in the
lessons; each folder here is where your skill goes and how it is graded.

| exercise | brief | you write | passes when |
|---|---|---|---|
| [01-first-skill](01-first-skill/README.md) | [lesson 2](../lesson-02-first-skill.md) | `skills/<name>/SKILL.md` | two more held-out tasks pass than with no skill |
| [02-generalise](02-generalise/README.md) | [lesson 3](../lesson-03-generalise.md) | `skills/<name>/SKILL.md` | all five held-out tasks pass, and the skill hardcodes none of their answers |

```bash
python tutorials/check.py 30-skill-authoring
```

Everything runs offline against the `mock` backend, which recognises a
rule by keyword. Passing means the instruction is at least specific; it
does not mean it is well written. See [the tutorials index](../../README.md#what-graded-actually-means).

Do not put notes or READMEs inside `skills/`: the evaluator loads every
skill folder there, and exercise 2's check reads every `.md` under it.
