## Why

Tests that pass do not prove the feature the product owner asked for. Without a mechanical link from each requirement to a test, requirements drift, tests go stale, and "green CI" means little. specgate makes that link a gate: a feature cannot merge unless every acceptance criterion (AC) in its PRD is specified, implemented, covered by a real test, and survives mutation.

## What Changes

- Add the `plugins/specgate` plugin and its `specgate check` CLI.
- Add seven gates, L0 to L6, that run in order and stop at the first red one.
- Add the marker convention: `# implements: AC-k` in source, `# covers: AC-k` in tests.
- Add a `trace.json` that maps each AC to its code, tests, coverage and killed mutants.
- Add a CI rule that every pull request adds or changes a knowledge-transfer doc under `docs/kt/`.
- Add the PRD frontmatter schema, `plugins/specgate/schema/prd.schema.json`.

## Capabilities

### New Capabilities

- `specgate`: the multi-layer acceptance gate (L0 schema, L1 static, L2 trace, L3 execution, L4 coverage, L5 mutation, L6 debate) plus the knowledge-transfer docs rule.

## Impact

- New code under `plugins/specgate/`.
- New workflows `.github/workflows/spec-gate.yml` and `.github/workflows/kt-docs.yml`.
- New docs under `docs/kt/specgate/`.
- Out of scope: running specgate against other repositories, and any change to the existing wikiskill runtime.
