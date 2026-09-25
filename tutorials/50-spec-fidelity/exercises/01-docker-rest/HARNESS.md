# Harness — OPS-1432 FX conversion function

<!-- Read by the ai-literacy-superpowers harness-enforcer agent
     (/harness-audit, or "use the harness-enforcer to verify the pr-scoped
     constraints in <this file>"). Deterministic constraints run the Tool
     line; agent constraints are judged by the enforcer reading the Rule.

     Tool paths are relative to the repository root. Replace EXERCISE with
     `tutorials/50-spec-fidelity/exercises/01-docker-rest` to judge your own
     work, or append `/solution` to judge the reference answer. -->

## Context

### Stack

- **Primary languages**: Python 3.12, stdlib only
- **Build system**: Docker (`impl/Dockerfile`, `python:3.12-slim`)
- **Test framework**: `unittest`, run from `impl/`
- **Container strategy**: one image, one process, non-root

### Conventions

- **Spec first**: `prd.md` → `openspec/changes/<id>/` → `impl/`, in that
  order. Code that no scenario asks for is a finding, not a bonus.
- **Traceability**: every spec requirement carries `Trace: PRD-<n>`; every
  test names its scenario with `Scenario: <exact scenario name>`.
- **Money**: `decimal.Decimal` in memory, JSON strings on the wire.

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

- **Rule**: Exactly one active change; `proposal.md` has `## Why` (50–1000
  chars) and `## What Changes`; every requirement sits in a delta section,
  has SHALL/MUST in its body and at least one WHEN/THEN scenario; every
  PRD ID is traced by a requirement and every requirement traces to a PRD ID.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage spec`
  (and, if the OpenSpec CLI is installed, `openspec validate --strict` from
  the exercise folder)
- **Scope**: pr

### Every scenario is tested, and tests pass

- **Rule**: Each `#### Scenario:` is named by exactly-matching
  `Scenario: <name>` in a test; no test names a scenario the spec lacks;
  every task in `tasks.md` is ticked; `impl/` tests pass; the Dockerfile
  builds from `python:3.12-slim`, runs as non-root, exposes 8080 and runs
  no `pip install`; `app.py` makes no network calls and uses no `float(`.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage build`
- **Scope**: pr

### Spec captures intent

- **Rule**: The OpenSpec change states the **problem** (why billing needs
  this), the **approach** (design.md) and the **outcome** (scenarios). The
  code in `impl/` delivers what the spec describes — compare each
  requirement to the code that implements it and flag significant
  divergence. A test that names a scenario but asserts something weaker
  than its THEN clause is divergence.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### No gold-plating

- **Rule**: `impl/` adds no endpoint, parameter, dependency, environment
  variable or behaviour that no spec requirement asks for. Non-goals in
  `prd.md` (auth, live rates, POST, batch, list-currencies) are absent from
  the code.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### Image actually runs

- **Rule**: `docker build` succeeds and the running container answers the
  Convert USD to EUR and Health check scenarios over real HTTP.
- **Enforcement**: unverified
- **Tool**: none yet — needs a Docker daemon; the manual smoke test is in
  the exercise README. Promote with `/harness-constrain` once CI has Docker.
- **Scope**: manual

---

## Garbage Collection

### Stale rates file

- **What it checks**: `impl/rates.json` was changed within the last 31 days.
- **Frequency**: monthly
- **Enforcement**: unverified
- **Tool**: none yet
- **Auto-fix**: false
