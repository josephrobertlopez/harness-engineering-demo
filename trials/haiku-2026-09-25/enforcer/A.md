All 5 PR-scoped constraints in HARNESS.md pass.

**Deterministic (ran first):**
1. **OpenSpec change is valid and traced** — PASS via `spec_fidelity.py --stage spec` (1 passed, 0 failed). Note: the secondary `openspec validate --strict` check couldn't run because the `openspec` CLI isn't installed in this environment — unverifiable, not a failure.
2. **Every scenario is tested, and tests pass** — PASS via `spec_fidelity.py --stage build` and independently via `unittest discover` (18/18 tests pass), matching all 18 scenarios in `openspec/changes/add-fx-convert/specs/fx/spec.md`.

**Agent-based (rule quoted, findings with file:line):**

3. **Spec captures intent** (HARNESS.md:74–79, *"Compare each requirement to the code that implements it and flag significant divergence..."*) — PASS. All 8 requirements trace to code, e.g. half-to-even rounding at `impl/app.py:19,21,76-83`; no test asserts less than its scenario's THEN clause.

4. **No gold-plating** (HARNESS.md:86–88, *"impl/ adds no endpoint, command, tool, argument, dependency, environment variable, file or behaviour that no spec requirement asks for..."*) — PASS. Only `/convert` and `/healthz` routes (`impl/app.py:51-55`), one env var `PORT`, no third-party deps, no PRD non-goals present.

5. **Requirements enforced in code, not comments** (HARNESS.md:95–98, *"Every numeric, rounding and error-handling requirement in the spec is implemented by code a test exercises..."*) — PASS. All money math uses `Decimal` with explicit `ROUND_HALF_EVEN` (`impl/app.py:77,82`); all 4 validation branches exercised by tests at `impl/tests/test_app.py:81-99`.

**Summary: 5/5 passed, 0 failed, 1 partial gap** (openspec CLI unavailable — doesn't affect the constraint's pass status since the primary tool covered it). Two constraints were out of scope and excluded as instructed: "PRD is OpenSpec-ready" (commit-scoped) and "Image actually runs" (manual, already marked unverified in HARNESS.md).
