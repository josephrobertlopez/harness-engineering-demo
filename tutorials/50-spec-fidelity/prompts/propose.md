---
description: Step 3 - derive the OpenSpec change from prd.md, then judge it
argument-hint: "<change-id, kebab-case, verb first, e.g. add-fx-convert>"
allowed-tools: Bash({{PYTHON}} {{JUDGE}}:*), Bash(openspec:*), Read, Write, Edit, Glob
---

Create the OpenSpec change `$ARGUMENTS` from `prd.md`. If `openspec` is
installed you may use `openspec new change $ARGUMENTS`; otherwise write the
files by hand. Either way, the result is:

```
openspec/changes/$ARGUMENTS/
├── proposal.md    ## Why (50-1000 characters, names the ticket and prd.md)
│                  ## What Changes (bullets)
│                  ## Capabilities → ### New Capabilities (one bullet per capability)
│                  ## Impact
├── design.md      # Design: … ## Technical Approach, ## Architecture Decisions
│                  (### Decision: … with the reason), ## File Changes
├── tasks.md       ## 1. <group>  then  - [ ] 1.1 <task>  (checkboxes, numbered)
└── specs/<capability>/spec.md
```

`spec.md` is an OpenSpec **delta**:

```markdown
## ADDED Requirements

### Requirement: <name>

<Behaviour with SHALL or MUST, in the body - not only in the heading.>

Trace: PRD-<n>

#### Scenario: <name>

- **WHEN** <situation>
- **THEN** <observable result>
```

Rules:
- One `### Requirement:` per PRD requirement is the default. Every
  `PRD-<n>` must be traced by at least one requirement; every requirement
  must trace to a real `PRD-<n>`. Nothing from the PRD's Non-goals.
- Every PRD `WHEN … THEN …` line becomes at least one `#### Scenario:`.
  Scenario names are unique across the change: tests will cite them
  verbatim.
- `tasks.md` includes one task to write a test per scenario, and a last
  task to get the judge green. Leave all boxes unticked.
- Write no implementation code.

Then run `{{PYTHON}} {{JUDGE}} . --stage spec` (and `openspec validate
--strict` if installed) and fix what they report. At most three rounds.
