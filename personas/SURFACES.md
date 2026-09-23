# Persona Export Surfaces

## What is "Generated"?

Exports are **machine-generated** from a single source of truth: the `*.persona.md` files in this directory. A persona exists in one tool-neutral form; from that form, we generate the surface-specific variants (agent, skill, card, JSON).

**Rule**: Export files are never hand-edited. If you need to change a persona, edit the source `*.persona.md` file and regenerate.

## Support Matrix

| Surface | Generated Path | Format | What It Is For | Status |
|---------|---|---|---|---|
| **Source** | `<id>.persona.md` | Markdown with YAML frontmatter | Single source of truth for all surfaces; tool-agnostic specification of the persona's role, voice, behavior | ✓ Primary |
| **Claude Code Agent** | `export/claude-agents/<id>.md` | Markdown (frontmatter + sections) | System prompt for a Claude Code subagent that embodies the persona | ✓ Generated |
| **Claude Code Skill** | `export/claude-skills/<id>/SKILL.md` | Markdown (frontmatter + sections) | Slash-command skill definition for invoking the persona from Claude Code | ✓ Generated |
| **Human Card** | `export/cards/<id>.md` | Markdown (readable one-pager) | Tutorial and reference documentation for humans learning about the persona | ✓ Generated |
| **Portable JSON** | `export/personas.json` | JSON (array of personas) | Machine-readable export for building system prompts in other tools (Codex, Cursor, raw API) | ✓ Generated |

## How Exports Are Generated

```bash
# Regenerate all exports
python personas/export.py

# Verify exports are current
python personas/export.py --check
```

The `export.py` script:
1. Parses all `*.persona.md` files (YAML frontmatter + Markdown body)
2. Generates four output formats from each persona
3. Writes outputs to `export/` subdirectories with a header comment warning against hand-editing

## Regeneration Rules

- **After editing a persona source file**: Run `python export.py` to regenerate all surfaces.
- **Before committing**: Run `python export.py --check` to verify exports are current. The build fails if exports are out of sync.
- **Never hand-edit an export**: If you edit a `export/` file, your changes will be overwritten when exports are regenerated. Always edit the source `*.persona.md` file instead.

## Persona Inventory

Eight personas, two families:

### Spec-Driven Family
These personas guide the journey from a vague idea to a testable specification.

| ID | Name | One-Liner |
|---|---|---|
| `spec-interrogator` | The Interrogator | Refuses to let an underspecified request become code |
| `spec-architect` | The Architect | Records only decisions that would cause incompatibility if two units chose independently |
| `spec-implementer` | The Implementer | Works from acceptance criteria; terse; speaks in file paths and criterion IDs; test-first |
| `spec-adversary` | The Adversary | Tries to break the spec before the code exists |

### Prompt-Upskilling Family
These personas improve the quality of work by evaluating it against frameworks, checking for anti-patterns, and measuring improvement.

| ID | Name | One-Liner |
|---|---|---|
| `prompt-critic` | The Critic | Scores an output on five rubric dimensions; Trust is a gate |
| `anti-pattern-scanner` | The Scanner | Checks work against seven named anti-patterns |
| `eval-designer` | The Eval Designer | Turns "this feels better" into a measurement |
| `scar-recorder` | The Scar Recorder | Captures a lesson after something breaks |

## File Structure

```
personas/
├── spec-interrogator.persona.md          # Source: spec-driven family
├── spec-architect.persona.md
├── spec-implementer.persona.md
├── spec-adversary.persona.md
├── prompt-critic.persona.md              # Source: prompt-upskilling family
├── anti-pattern-scanner.persona.md
├── eval-designer.persona.md
├── scar-recorder.persona.md
├── export.py                             # Generator script (stdlib-only, Python 3.12+)
├── SURFACES.md                           # This file
├── README.md                             # User documentation
└── export/                               # Generated exports
    ├── claude-agents/
    │   ├── spec-interrogator.md
    │   ├── spec-architect.md
    │   └── ...
    ├── claude-skills/
    │   ├── spec-interrogator/SKILL.md
    │   ├── spec-architect/SKILL.md
    │   └── ...
    ├── cards/
    │   ├── spec-interrogator.md
    │   ├── spec-architect.md
    │   └── ...
    └── personas.json                     # Single JSON file with all personas
```

## Consistency Checks

The build CI runs:
```bash
python personas/export.py --check
```

This verifies:
- All source files can be parsed
- All exports exist and match the latest source
- Exits with code 0 if exports are current, code 1 if not

If the check fails, run `python personas/export.py` locally to regenerate, then commit the updated exports.
