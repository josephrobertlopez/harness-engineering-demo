---
description: Step 5 - the agent half of the judge - verify HARNESS.md's agent constraints
allowed-tools: Bash({{PYTHON}} {{JUDGE}}:*), Read, Glob, Grep
---

If the `harness-enforcer` agent from the ai-literacy-superpowers plugin is
available, use it: verify every `pr`-scoped constraint in `HARNESS.md`
against this folder, deterministic ones first, and report its output.

If it is not available, do the same job yourself, read-only, and say at the
top that this is a stand-in for the plugin's agent:

1. Read `HARNESS.md`. For each constraint with `Enforcement: deterministic`,
   run its `Tool` command and report PASS or FAIL.
2. For each constraint with `Enforcement: agent`, quote its Rule, then
   check it against `prd.md`, `openspec/changes/*/` and `impl/`. For every
   test that cites a scenario, compare its assertions to the scenario's
   THEN clause and flag any that assert less. Look for code paths,
   endpoints, arguments or dependencies no requirement asks for.
3. Skip `unverified` constraints, listing them as UNCHECKED.

Report in this format, with `file:line` for every finding:

```text
## Constraint Results

### <Constraint name> — PASS | FAIL | UNCHECKED
Enforcement: <deterministic | agent | unverified>
Findings:
- <file>:<line> — <what is wrong>

---
Summary: <n> passed, <n> failed, <n> unchecked
```

Do not modify any file.
