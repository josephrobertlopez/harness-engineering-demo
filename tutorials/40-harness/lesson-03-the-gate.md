# Lesson 3 — The gate

The gate is the accept/reject decision. It lives in `src/wikiskill/gating.py`,
in a function called `decide()`:

```python
def decide(
    *,
    val_candidate: float,
    val_incumbent: float,
    r_best: float,
    margin: float = 0.0,
) -> GateDecision:
    baseline = max(val_incumbent, r_best)
    if val_candidate > baseline + margin:
        return GateDecision(accepted=True, reason=None, r_best_after=val_candidate)
    reason = "no_improvement" if val_candidate <= baseline else "below_margin"
    return GateDecision(accepted=False, reason=reason, r_best_after=baseline)
```

Translate that to English: the candidate is accepted if it beats both the
incumbent (the current skill set) and `r_best` (the best we have ever seen),
with optional margin to demand more.

## Why paired re-measurement

The paper compares the candidate against a stored `R_best`. This repo does
something different: it re-measures the incumbent in the same batch as the
candidate.

Why? The benchmark has five validation tasks. One task can be a twenty-point
swing. If you compare a candidate measured today against a score from two
iterations ago, you accept noise as learning — especially because an accepted
skill becomes the parent of every later proposal, so admitted noise compounds
into the lineage.

Re-measuring doubles the validation cost. On five tasks that is nothing. The
guarantee it buys is real: every number the gate sees is fresh.

## Margin and ties

`gate_margin` can be set to demand a minimum improvement:

```bash
python -m wikiskill.cli ... run --gate-margin 0.05
```

Ties (candidate == incumbent) are always rejected. A proposal that does not
improve is not an improvement, and the cost of a false acceptance exceeds the
cost of delaying a real improvement by one iteration.

## Budget check

Before the gate ever runs evaluation, `check_budget()` rejects oversized
proposals:

```python
def check_budget(
    *,
    skill_bytes: int,
    skillset_bytes: int,
    skill_budget: int,
    skillset_budget: int,
) -> str | None:
    """Reject oversized proposals before spending anything on evaluation."""
    if skill_bytes > skill_budget:
        return f"budget: skill is {skill_bytes}B, limit {skill_budget}B"
    if skillset_bytes > skillset_budget:
        return f"budget: skill set would be {skillset_bytes}B, limit {skillset_budget}B"
    return None
```

Skills only accumulate, so without a ceiling the injected block eventually
dominates the inference prompt and quality degrades from dilution. Rejecting
here costs zero evaluation tokens. The rejection is recorded in
`skill-impact.md`, which the proposer reads next iteration — a bounded repair
turn.

## What happens after acceptance

If the candidate passes, `HEAD.json` is updated to point at the new skill set.
If it fails, `HEAD` does not move. There is no rollback to implement because
there is nothing to undo: the candidate lived in its own content-addressed
snapshot, and rejection simply never points at it.

---

Next: [Lesson 4 — Rollback and resume](lesson-04-rollback-resume.md)
