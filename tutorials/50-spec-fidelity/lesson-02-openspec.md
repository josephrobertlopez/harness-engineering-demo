# Lesson 2 — OpenSpec in ten minutes, and what the judge enforces

[OpenSpec](https://github.com/Fission-AI/OpenSpec) is a spec-driven
development tool: before code, you write a **change** — a folder that says
why, what, how, and in which order — and the AI implements against it.
This lesson covers only the parts this track uses. The upstream
[concepts guide](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md)
is the reference.

## The change folder

```
openspec/
├── config.yaml                  project context + per-artifact rules (start.py writes this)
├── specs/                       the current truth; empty in a new project
└── changes/
    └── add-fx-convert/          one folder per change, kebab-case verb-first
        ├── proposal.md          ## Why · ## What Changes · ## Capabilities · ## Impact
        ├── design.md            technical approach and the decisions behind it
        ├── tasks.md             - [ ] 1.1 numbered checkbox tasks
        └── specs/
            └── fx/              one folder per capability
                └── spec.md      a DELTA: what this change adds or modifies
```

The spec is a **delta**, not a whole document. It says what changes:

```markdown
## ADDED Requirements

### Requirement: Half-to-even rounding

The service SHALL round `result` to 2 decimal places and `rate` to 6 decimal
places using round-half-to-even, computing `result` from the unrounded rate.

Trace: PRD-2

#### Scenario: Tie rounds down to even

- **WHEN** a client converts `0.125` USD to USD
- **THEN** the result is `"0.12"`
```

Four headers matter: `## ADDED|MODIFIED|REMOVED|RENAMED Requirements`,
`### Requirement: <name>`, `#### Scenario: <name>`, and the
**WHEN**/**THEN** bullets. Get a heading level wrong and the requirement or
scenario is not parsed as one. `openspec validate` usually says so — if you
run it.

## The workflow in Claude Code

```bash
npm install -g @fission-ai/openspec@latest      # Node 20.19+
cd ~/fidelity/ops-1432 && openspec init --tools claude
```

`init` adds `/opsx:*` commands and skills under `.claude/`, and keeps the
`openspec/config.yaml` that `start.py` already wrote. Then, in Claude Code:

| command | does | this track uses it for |
|---|---|---|
| `/opsx:explore` | thinks with you, writes nothing | optional, before the PRD |
| `/opsx:propose <id>` | writes proposal, specs, design, tasks — **and stops** | PRD → change |
| `/opsx:apply` | implements the tasks | change → `impl/` |
| `/opsx:archive` | merges the delta into `openspec/specs/` | after you are done (the judge ignores `changes/archive/`) |

`/opsx:propose` deliberately stops before code. That pause is where you run
`--stage spec` and fix the change *before* anything depends on it.

No Node? Write the four files by hand. The judge does not care who wrote
them, and neither does OpenSpec.

## What `openspec validate` checks, and what the judge adds

`openspec validate --strict` (from the workspace) is the upstream
authority. The judge re-implements the subset that matters here, so it can
run in CI with no Node, then adds the tracing OpenSpec does not know about.

| rule | OpenSpec | judge `--stage spec` |
|---|---|---|
| `## Why` is 50–1000 characters | ✓ | ✓ |
| `## What Changes` is present and non-empty | ✓ | ✓ |
| at least one delta section | ✓ | ✓ |
| requirement body has SHALL or MUST (not only the header) | ✓ (`--strict`) | ✓ |
| every requirement has a `#### Scenario:` | ✓ | ✓ |
| a requirement outside a delta section is reported | ✓ | ✓ |
| scenario has WHEN and THEN | — | ✓ |
| `tasks.md` has checkbox tasks | warns | ✓ |
| exactly one active change | — | ✓ |
| every `PRD-n` is traced; every requirement traces to a real `PRD-n` | — | ✓ |

All three reference solutions pass `openspec validate --strict` on
OpenSpec 1.13.2 as well as the judge. If the two ever disagree, OpenSpec is
right about OpenSpec, and the judge needs fixing.

## `config.yaml`: teach the convention once

OpenSpec shows `context` and per-artifact `rules` to the AI each time it
writes an artifact. `start.py` puts the track's conventions there:

```yaml
rules:
  specs:
    - 'End every requirement body with a line "Trace: PRD-<n>" naming the prd.md requirement(s) it implements'
```

Two things bite here:

- **Quote any rule containing `: `.** Unquoted, YAML parses
  `...a line "Trace: PRD-<n>"...` as a mapping. OpenSpec then prints *"Rules
  for 'specs' must be an array of strings, ignoring this artifact's rules"*
  and carries on, and the AI never sees the rule. Check with
  `openspec instructions specs --change <id>` and look for `<rules>`.
- **Rules are advice to the AI, not validation.** `openspec validate` does
  not check them. The judge does.

## What makes a PRD "OpenSpec-ready"

`--stage prd` checks the PRD against what the spec will need, before you
spend a `/opsx:propose` on it:

| check | why |
|---|---|
| `## Problem`, `## Requirements`, `## Non-goals`, `## Open questions` | Non-goals are how you catch gold-plating later |
| each requirement is `### PRD-<n>: <title>` | the trace target |
| each has SHALL or MUST | it becomes a requirement body |
| each has a WHEN … THEN | it becomes a `#### Scenario:` |
| none of the ticket's vague words (`rubric.json`) | a vague word in the PRD is a guess in the code |
| no `TBD` left in Open questions | an open question is a requirement nobody owns |
| every stakeholder fact pinned down (`rubric.json`) | you asked, you got an answer, it must be written down |

The last row is the one that teaches. The findings name the stakeholder
answer you missed (`stakeholder-answers.md Q4`), so you can see which
question you did not think to ask.

---

Next: [Lesson 3 — The loop with Claude](lesson-03-the-loop.md)
