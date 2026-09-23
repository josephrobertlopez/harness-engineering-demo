"""Validation gating and rollback (the paper's Eq. 4).

    S_k  =  S'_k       if  R(T_val,k) > R_best
            S_{k-1}    otherwise

Two deliberate implementation choices sit on top of that formula.

**Paired re-measurement.** The paper compares the candidate against a stored
``R_best``. Here the incumbent is re-measured in the same batch as the
candidate, and the comparison is candidate-vs-incumbent. With a five-task
validation split one task is a twenty-point swing, and ``temperature`` is
removed on Opus 5 / Sonnet 5 so sampling cannot be pinned -- comparing against
a score measured two iterations ago accepts drift as if it were learning, and
because an accepted skill becomes the parent of every later proposal, that
noise compounds into the lineage. Re-measuring doubles validation cost, which
on five tasks is nothing.

**Ties are rejected**, and ``gate_margin`` can demand more. A rejected good
proposal costs one iteration; an accepted bad one poisons everything after it.

Rollback itself is not implemented here because there is nothing to undo: the
candidate lives in its own content-addressed snapshot and rejection simply
never points HEAD at it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GateDecision:
    accepted: bool
    reason: str | None
    r_best_after: float


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


def check_budget(
    *,
    skill_bytes: int,
    skillset_bytes: int,
    skill_budget: int,
    skillset_budget: int,
) -> str | None:
    """Reject oversized proposals before spending anything on evaluation.

    Skills only accumulate, so without a ceiling the injected block eventually
    dominates the inference prompt and quality degrades from dilution -- which
    looks like "the method does not work". Rejecting here costs zero
    evaluation tokens, and the rejection is recorded in the skill-impact
    ledger, which is in the proposer's context next iteration.
    """
    if skill_bytes > skill_budget:
        return f"budget: skill is {skill_bytes}B, limit {skill_budget}B"
    if skillset_bytes > skillset_budget:
        return f"budget: skill set would be {skillset_bytes}B, limit {skillset_budget}B"
    return None
