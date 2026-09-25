---
description: Step 2b - adversarial review of prd.md before it becomes a spec
---

Read `personas/spec-adversary.persona.md` and act as that persona.

Review `prd.md` for readiness to become an OpenSpec change. Do not edit any
file. For each `PRD-<n>`:

1. Name any input, state or failure it does not cover (null, empty,
   boundary values, concurrency, a missing dependency, a timeout).
2. Name any way a test could pass without the behaviour existing — an
   acceptance line too weak to fail.
3. Name any contradiction with another requirement or with a Non-goal.

Then list anything in `interview.md` that no requirement reflects.

Rank findings critical / major / minor. For each, say whether it needs a
product-owner decision (→ `/fidelity:interrogate`) or only a rewrite of
`prd.md` (→ `/fidelity:prd`). Do not propose code.
