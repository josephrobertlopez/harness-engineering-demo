# Lesson 2 — Scoring an output on five dimensions

"This output is bad" is not actionable. The rubric gives you five axes so you can
say *which* kind of bad, and therefore what to change.

## The five dimensions

| | Dimension | The question |
|---|---|---|
| **Π** | Precision | Is it technically correct and complete? |
| **H** | Helpfulness | Does it serve the user's actual need? |
| **M** | Meaning | Is the structural framing clear and consistent? |
| **I** | Immediacy | How quickly does the user get value? |
| **T** | Trust | Would a domain expert believe this? |

Score each 0–100.

## Trust is a gate, not a contributor

```
Composite = (Π + H + M + I) × (T / 100)
```

If **T = 0, the composite is 0** regardless of everything else. A beautifully
structured, instantly readable, comprehensive answer built on a fabricated
number is worth nothing — it is worse than nothing, because it will be
believed.

This is the single most useful thing in the framework. It stops you trading
correctness for polish, because the arithmetic will not let you.

> **A note on scales.** You will see this rubric written two ways — each
> dimension 0–20 summing to 100, or each 0–100 with Trust applied as the
> multiplier above. This track uses the second. Pick one and write it down,
> because a team silently using both will argue about numbers that were
> never comparable.

## The named failure patterns

These are worth memorising, because you will produce all of them:

| Pattern | Shape | Fix |
|---|---|---|
| **Hallucinated data** | T=0 → composite 0 | cite or drop it |
| **Beautiful lies** | M=90, T=20 | the polish is hiding the problem |
| **Correct but useless** | Π=95, H=15 | answered a question nobody asked |
| **Raw dump** | Π=90, I=10 | correct, and nobody will read it |
| **Generic boilerplate** | everything ~50 | says nothing false and nothing useful |

Notice that three of the five score *well* on something. That is why a single
"quality" number hides them and five dimensions do not.

## How to actually use it

1. **Baseline.** Score the current output. Write the numbers down.
2. **Set a floor.** MVP ≥ 75, production ≥ 85, regulated ≥ 90.
3. **Score changes as deltas**, with a reason: `Π: +8 — now handles the empty
   case`. A delta you cannot justify in a clause is not a real improvement.
4. **Ratchet the floor up, never down.** Lowering the bar to make a change
   pass is the failure mode this whole discipline exists to prevent.

## Try it

Score the two outputs in the exercise folder before reading lesson 3. They
are designed so the composite ordering surprises you.

---

Next: [Lesson 3 — The seven anti-patterns](lesson-03-anti-patterns.md)
