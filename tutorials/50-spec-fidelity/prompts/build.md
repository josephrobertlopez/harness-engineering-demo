---
description: Step 4 - implement the OpenSpec change test-first in impl/, then judge everything
allowed-tools: Bash({{PYTHON}}:*), Bash({{PYTHON}} {{JUDGE}}:*), Read, Write, Edit, Glob, Grep
---

Read `personas/spec-implementer.persona.md` and act as that persona.
Where the persona and this prompt disagree -- test naming, file layout,
test framework, what to do when the spec looks wrong -- **this prompt
wins**.

Implement the single change under `openspec/changes/` in `impl/`.

Layout the judge expects:

```
impl/
├── <your modules>.py
├── tests/__init__.py            (empty)
└── tests/test_<area>.py         unittest.TestCase classes
```

Tests run from `impl/` with `{{PYTHON}} -m unittest discover -s tests -t .`

Test first, one scenario at a time:

1. For each `#### Scenario: <name>` in the spec, write one test **method on
   a `unittest.TestCase` class** whose docstring's first line is exactly
   `Scenario: <name>` — same spelling, same case. Module-level pytest-style
   functions are not collected and do not count. The test must assert the
   scenario's THEN clause, not a weaker stand-in; a tagged test that
   asserts nothing, or is skipped, does not count either.
2. Run it and see it fail. Then write the code that makes it pass.
3. Tick the matching box in `tasks.md` (`- [x]`).

Rules:
- Read `HARNESS.md` before writing code: it says how the code is judged.
- Use no dependency the PRD does not name.
- Implement nothing the spec does not ask for. If the spec seems to be
  missing something, stop and tell me instead of adding it.
- Do not edit `prd.md` or the spec to match the code. If they are wrong,
  say so and stop.

Finish with `{{PYTHON}} {{JUDGE}} .` and fix what it reports, at most three
rounds. Report the final judge summary line.
