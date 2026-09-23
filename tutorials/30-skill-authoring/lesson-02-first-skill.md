# Lesson 2 — Your first skill

## Measure before you write

Never start by writing. Start by finding out what is actually broken.

```bash
# What does the agent score with no help at all?
python -m wikiskill.cli --workspace /tmp/ws --backend mock eval --split test --skills none
```

On Windows PowerShell use `$env:PYTHONPATH="src"` first; bash users
`export PYTHONPATH=src`. Output:

```
test (none): 0.000 over 5 task(s)
  FAIL iso_z-3          field 'timestamp': expected '2026-03-07T06:30:12Z', got '2026-03-07T06:30:12'
  FAIL rec_prefix-3     field 'status': expected 'reversed', got 'unknown'
  FAIL page_two-3       field 'owner': expected 'okonkwo', got 'decoy-30'
  FAIL round_even-3     field 'amount': expected 40.48, got 40.49
  FAIL idem_key-3       field 'idempotency_key': expected 'REC-4843:reconcile', got None
```

Five failures, and each one names the field and the wrong value. That list
*is* your specification. You are not guessing what to write.

> Note this is the **test** split — the one nothing has been tuned against.
> Scoring yourself on data you designed against is the oldest way to be
> wrong with confidence.

## Write it

Create `tutorials/30-skill-authoring/exercises/01-first-skill/skills/<your-name>/SKILL.md`.

The folder layout matters — `--skills-dir` expects `<skill-name>/SKILL.md`:

```
exercises/01-first-skill/skills/
└── house-rules/
    └── SKILL.md
```

Write rules for **at least two** of the five failures. Be specific: name the
format, show the transformation. "Format timestamps correctly" is not a rule,
it is a wish.

## Measure again

```bash
python -m wikiskill.cli --workspace /tmp/ws --backend mock \
  eval --split test --skills-dir tutorials/30-skill-authoring/exercises/01-first-skill/skills
```

The failures you fixed disappear from the list. The ones you did not stay.

## Check it

```bash
python tutorials/check.py 30-skill-authoring/01-first-skill
```

Passing requires **at least two more tasks passing than baseline**. Not all
five — this lesson is about closing the loop, not about being thorough.

## What to notice

You did not improve the model. You did not change a prompt template. You
wrote down something the model had no way to know, and a measurement
confirmed it landed. That is the entire mechanism, and the rest of this
track is about the ways it goes wrong.

---

Next: [Lesson 3 — Generalise, don't memorise](lesson-03-generalise.md)
