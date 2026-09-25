---
description: Run the deterministic fidelity judge and explain each finding (edits nothing)
allowed-tools: Bash({{PYTHON}} {{JUDGE}}:*), Read
---

!`{{PYTHON}} {{JUDGE}} . --exit-zero`

Above is the deterministic judge's report for this workspace. Do not edit
any file. For each finding:

1. Say in one sentence what it means.
2. Name the step that caused it and the command that fixes it:
   `/fidelity:interrogate` (a fact was never asked for), `/fidelity:prd`,
   `/fidelity:propose`, or `/fidelity:build`.
3. If fixing it would mean changing an earlier artifact to match a later
   one (e.g. editing the spec to match the code), say so and recommend
   against it.

If everything passes, say so and point at `/fidelity:enforce` — the
deterministic judge checks shape and tracing, not meaning.
