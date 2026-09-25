# Harness — DEVX-311 MCP server for CLIs

<!-- Read by the ai-literacy-superpowers harness-enforcer agent
     (/harness-audit, or /fidelity:enforce in a start.py workspace).
     Deterministic constraints run the Tool line; agent constraints are
     judged by the enforcer reading the Rule.

     This file is given to the developer, so it states how the work is
     judged and never what the product owner decided: those answers have to
     be asked for. The exercise-specific rules live in rubric.json, which
     the judge reads from the repo and the workspace never contains.

     Tool paths are relative to the repository root; start.py rewrites
     them for a workspace. EXERCISE is this exercise's folder, or its
     solution/ folder to judge the reference answer. -->

## Context

### Stack

- **Primary languages**: Python 3.12
- **Protocol**: MCP over the transport the spec names
- **Test framework**: `unittest`, run from `impl/` with
  `python -m unittest discover -s tests -t .`; fake the command runner so
  tests do not depend on which CLIs are installed

### Conventions

- **Spec first**: `prd.md` → `openspec/changes/<id>/` → `impl/`, in that
  order. Code that no scenario asks for is a finding, not a bonus.
- **Traceability**: every spec requirement carries `Trace: PRD-<n>`; every
  test's docstring starts `Scenario: <exact scenario name>`.
- **The interview is the source**: `interview.md` records what the product
  owner said. A decision that is not in it has not been made.

---

## Constraints

### PRD is OpenSpec-ready

- **Rule**: Every requirement in `prd.md` is `### PRD-<n>: <title>` with a
  SHALL or MUST, a WHEN/THEN acceptance line, and none of the ticket's
  vague words; every decision the product owner made is written down, and
  none is contradicted.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage prd`
- **Scope**: commit

### OpenSpec change is valid and traced

- **Rule**: Exactly one active change; `proposal.md` has `## Why` (50–1000
  chars) and `## What Changes`; every requirement sits in a delta section,
  has SHALL/MUST in its body and at least one WHEN/THEN scenario; scenario
  names are unique; every requirement has a `Trace: PRD-<n>` line naming
  real PRD ids, and every PRD id has a requirement of its own.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage spec`
  (and, if the OpenSpec CLI is installed, `openspec validate --strict`)
- **Scope**: pr

### Every scenario is tested, and tests pass

- **Rule**: Each `#### Scenario:` has a `unittest.TestCase` test whose
  docstring's first line is `Scenario: <exact name>`, which asserts
  something, runs, and passes (a skipped test does not count); no test
  names a scenario the spec lacks; every task in `tasks.md` is ticked; the
  exercise's implementation rules hold.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage build`
- **Scope**: pr

### Spec captures intent

- **Rule**: The OpenSpec change states the **problem**, the **approach**
  (design.md) and the **outcome** (scenarios), and `impl/` delivers what
  the spec describes. Compare each requirement to the code that implements
  it and flag significant divergence. For every test that cites a
  scenario, compare its assertions with the scenario's THEN clause: a test
  that asserts less than the THEN says is divergence.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### No gold-plating

- **Rule**: `impl/` adds no endpoint, command, tool, argument, dependency,
  environment variable, file or behaviour that no spec requirement asks
  for, and nothing the PRD lists under Non-goals.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### The command surface is exactly the spec's

- **Rule**: List every argument vector the server can build. Each must be
  one the spec names, with caller input only in the positions the spec
  allows. No caller-controlled binary, subcommand or flag; no way to run a
  command outside the directory the spec confines it to.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### Connects in Claude Code

- **Rule**: `claude mcp list` shows the server as connected after
  registering it the way the spec says.
- **Enforcement**: unverified
- **Tool**: none yet — needs a signed-in Claude Code.
- **Scope**: manual
