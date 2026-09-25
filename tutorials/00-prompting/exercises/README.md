# Track 00 exercises

Two graded exercises for [track 00](../README.md). Each folder holds the
brief (`README.md`), the check that grades it (`check.py`), and a
`solution/` the test suite uses to prove the exercise is solvable. Leave
`solution/` alone until you have an answer of your own.

| exercise | you write | graded by |
|---|---|---|
| [01-diagnose](01-diagnose/README.md) | `answers.md`: the anti-pattern and rubric dimension behind three bad outputs | matching your answers against the lesson 3 catalogue |
| [02-specificity](02-specificity/README.md) | `rules/instructions/SKILL.md`: two vague rules rewritten so an agent can act on them | scoring them on the held-out split with the offline mock backend; passes when both land (2 of 5 tasks, from a baseline of 0) |

```bash
python tutorials/check.py 00-prompting                  # both
python tutorials/check.py 00-prompting/01-diagnose      # one
```

Both run offline with no API key. A fresh checkout fails both on purpose,
with a hint: the folders you write into ship empty.
