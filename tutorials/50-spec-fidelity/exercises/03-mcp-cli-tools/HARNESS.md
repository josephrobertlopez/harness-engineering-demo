# Harness — DEVX-311 MCP server for git and rg

<!-- Read by the ai-literacy-superpowers harness-enforcer agent
     (/harness-audit, or "use the harness-enforcer to verify the pr-scoped
     constraints in <this file>"). Deterministic constraints run the Tool
     line; agent constraints are judged by the enforcer reading the Rule.

     Tool paths are relative to the repository root. Replace EXERCISE with
     `tutorials/50-spec-fidelity/exercises/03-mcp-cli-tools` to judge your
     own work, or append `/solution` to judge the reference answer. -->

## Context

### Stack

- **Primary languages**: Python 3.12, stdlib only (the MCP SDK is allowed
  if you choose it; the reference does not use it)
- **Protocol**: MCP `2025-06-18` over stdio, newline-delimited JSON-RPC 2.0
- **External binaries**: `git`, `rg` — and nothing else
- **Test framework**: `unittest`, run from `impl/`, with a fake runner

### Conventions

- **Spec first**: `prd.md` → `openspec/changes/<id>/` → `impl/`.
- **Traceability**: every spec requirement carries `Trace: PRD-<n>`; every
  test names its scenario with `Scenario: <exact scenario name>`.
- **stdout is the protocol channel**: nothing but JSON-RPC is ever written
  to it; diagnostics go to stderr.

---

## Constraints

### PRD is OpenSpec-ready

- **Rule**: Every requirement in `prd.md` has a `PRD-<n>` ID, a SHALL or
  MUST, a WHEN/THEN acceptance, none of the ticket's vague words, and every
  fact from `stakeholder-answers.md` is pinned down.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage prd`
- **Scope**: commit

### OpenSpec change is valid and traced

- **Rule**: One active change; valid proposal; every requirement in a delta
  section with SHALL/MUST and a WHEN/THEN scenario; PRD ↔ spec tracing
  complete in both directions.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage spec`
  (and `openspec validate --strict` if the OpenSpec CLI is installed)
- **Scope**: pr

### Every scenario is tested, and tests pass

- **Rule**: Scenario ↔ test tagging complete in both directions; every task
  ticked; tests pass; `server.py` contains no `shell=True`, `os.system`,
  `os.popen`, `exec(` or `eval(`; declares protocol `2025-06-18`, the 8000
  cap and the 10 s timeout; `.mcp.json` registers the server with `--root`.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage build`
- **Scope**: pr

### Spec captures intent

- **Rule**: The change states the **problem** (the old any-shell server),
  the **approach** (design.md) and the **outcome** (scenarios), and
  `impl/` delivers it. Compare each requirement to the code: every tool's
  argv is a fixed list with user input only after `-e` or `--`; the path
  check runs before the runner; tool failures are `isError` results while
  only unknown tools and methods are JSON-RPC errors.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### Read-only surface

- **Rule**: No tool can cause a write: no git subcommand other than
  `status`, `log` and `diff`; no rg flag that writes or executes (`--pre`,
  `--replace` to a file); no argument that lets the caller choose the
  subcommand or the binary.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### No gold-plating

- **Rule**: No tool, CLI, transport, MCP capability (resources, prompts) or
  argument beyond the four tools the PRD lists.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### Connects in Claude Code

- **Rule**: `claude mcp list` shows `cli-tools` as connected after
  registering it with the command in the exercise README.
- **Enforcement**: unverified
- **Tool**: none yet — needs a signed-in Claude Code. Promote with
  `/harness-constrain` if your CI has one.
- **Scope**: manual
