---
name: "specgate: debate"
description: "Explain the L6 debate layer (not run by the CLI)"
allowed-tools: Bash(specgate:*)
category: "Validation"
tags: ["debate", "adversarial", "validation"]
---

L6 is the adversarial debate layer. **The `specgate` CLI does not run it:** `specgate check --layers L6` returns no findings and exits 0, and CI does not enforce it yet. There is no `specgate debate` subcommand.

Do this instead:

1. Run the deterministic gates: `specgate check --change openspec/changes/<feature> --layers L0-L5`.
2. Read `prd.md` and the spec as an adversary. Ask:
   - Are the AC assumptions grounded in the requirements?
   - Is the AC language precise and unambiguous?
   - Do the ACs cover both the happy path and the error cases?
   - Do the ACs avoid over-specifying the implementation?
   - Would the tests catch real bugs in a bad implementation?
3. Record what you find in the change's `proposal.md`.

Background and the calibration result: `docs/kt/specgate/README.md`.
