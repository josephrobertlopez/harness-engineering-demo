## HARNESS.md verification results

**4 passed, 2 failed, 1 unchecked (out of scope).**

| Constraint | Type | Scope | Result |
|---|---|---|---|
| PRD is OpenSpec-ready | deterministic | commit | PASS |
| OpenSpec change is valid and traced | deterministic | pr | PASS *(openspec CLI half unavailable — gap noted below)* |
| Every scenario is tested, and tests pass | deterministic | pr | PASS |
| Spec captures intent | agent | pr | **FAIL** |
| No gold-plating | agent | pr | **FAIL** |
| Requirements enforced in code, not comments | agent | pr | PASS |
| Image actually runs | unverified | manual | UNCHECKED — no Docker daemon, out of PR scope |

### Deterministic checks
- `spec_fidelity.py --stage prd/spec/build` all pass (exit 0).
- Test suite verified directly: `impl/tests/test_app.py` — 18 tests, all pass.
- **Gap**: `openspec validate --strict` (HARNESS.md:57-58) couldn't run — `openspec` CLI not installed (`which openspec` → exit 127). Conditional per the rule text, so it didn't fail the constraint, but that half of the tooling wasn't actually exercised.

### Agent checks — both failures trace to one root cause

**"Spec captures intent"** (HARNESS.md:74-79, quoted: *"impl/ delivers what the spec describes... flag significant divergence"*) — **FAIL**
`impl/app.py:53-54` implements `GET /currencies` returning `{"currencies": sorted(self.rates)}`. No `PRD-<n>`, no proposal/spec requirement, no `#### Scenario:`, no test references it.

**"No gold-plating"** (HARNESS.md:86-88, quoted: *"impl/ adds no endpoint... that no spec requirement asks for, and nothing the PRD lists under Non-goals"*) — **FAIL**
Same code, `impl/app.py:53-54`, directly contradicts `prd.md:118`, which explicitly lists **"a list-currencies endpoint"** under Non-goals. This isn't a borderline call — it's the implementation doing the one thing the PRD says not to do.

**"Requirements enforced in code, not comments"** (HARNESS.md:95-98) — PASS. Every rounding/arithmetic/error-handling requirement was traced to executing, tested code (rounding via `ROUND_HALF_EVEN` on the unrounded rate, cross-rate math, startup-only rate loading, invalid-amount rejection) with matching assertions in `test_app.py`.

### Fix
Remove `impl/app.py:53-54`. If a currencies-listing capability is actually wanted, it needs to go back through `prd.md` → OpenSpec → `impl/`, per the harness's "spec first" convention (HARNESS.md:28-29) — not be added directly to the implementation.
