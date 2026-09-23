# Lesson 4 — Budgets and failure modes

Four ways a correct skill still gets rejected.

## 1. It is too long

Skills only accumulate. Nothing in this harness deletes one. By iteration
eight an unbounded skill set dominates the inference prompt, and quality
degrades from dilution — which looks exactly like "the method does not work".

So there are hard ceilings, checked in `gating.py:check_budget` **before**
anything is evaluated:

| limit | default |
|---|---|
| one skill | 8 KB |
| the whole set | 32 KB |

An over-budget proposal is rejected with `reject_reason="budget"` at zero
evaluation cost, and the rejection is written to `skill-impact.md` — which
is in the proposer's context next iteration. The system teaches itself that
verbosity gets refused.

## 2. It restates the analysis instead of instructing

The wiki page explains *why* something fails: symptom, root cause, evidence,
trace ids. That is the right content for a wiki page and the wrong content
for a skill.

A skill is an instruction to follow at the moment of acting. Copying the
root-cause paragraph into it spends the budget on reasoning the agent does
not need and cannot use.

> Wiki: *"Model rounds `amount_raw` values ending in exactly `.5` using
> round-half-up, producing 2.35 where the grader expects 2.34."*
>
> Skill: *"Round money half-to-even at two decimals. `2.345` → `2.34`."*

Same knowledge. Only one of them is actionable at the point of use.

## 3. It duplicates what the environment already says

Lesson 1's table: the model passed `rec_prefix` and `page_two` unaided,
because an error message and a `more_pages` flag told it what to do. A skill
covering those costs budget and changes no outcome.

## 4. It is neutral, and neutral is rejected

The gate accepts only a **strict** improvement — a tie is a rejection
(`gating.py:decide`). That is deliberate: with a five-task validation split
one task is a twenty-point swing, and an accepted skill becomes the parent
of every later proposal, so noise admitted once compounds into the lineage.

The paper itself lists this as a limitation: a neutral proposal that would
have enabled a later gain is thrown away. This implementation keeps the
strictness rather than quietly inventing a policy the paper did not evaluate.

## Where to go next

- [`docs/EXTENDING.md`](../../docs/EXTENDING.md) — point the harness at your own tasks
- [Track 40 — the harness](../40-harness/README.md) — how the gate and rollback work
- [Track 00 — prompting](../00-prompting/README.md) — the same measure-change-measure loop, applied to prompts
