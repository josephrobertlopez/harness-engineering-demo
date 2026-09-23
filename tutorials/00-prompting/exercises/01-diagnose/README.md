# Exercise 1 — Diagnose

Three outputs from a real-ish system. For each, name the anti-pattern
(AP1–AP7) and the rubric dimension it primarily damages (Π, H, M, I, or T).

Write your answers to `answers.md` in this folder, one line per scenario:

```
1. AP?  dimension: ?
2. AP?  dimension: ?
3. AP?  dimension: ?
```

Then: `python tutorials/check.py 00-prompting/01-diagnose`

---

## Scenario 1

You asked for a competitive analysis of five vendors. The output rates your
own company 5/5 on every one of eight dimensions, and each competitor 3/5 or
below on all eight. The prose is well-organised and reads confidently.

## Scenario 2

A generated settings page has a row labelled "Export data" styled with
`cursor: pointer`, hover highlighting, and a chevron. Clicking it does
nothing — there is no handler attached.

## Scenario 3

A pricing module computes margin correctly for the client discussed in the
conversation. Reading the source, the tax rate is written as
`const TAX_RATE = 0.0825`. The system is sold to customers in eleven
jurisdictions.
