# Personas

Eight personas for engineering teams, organized into two families: **spec-driven** (for building the right thing) and **prompt-upskilling** (for building it well).

## What is a Persona?

A persona is a reusable role you invoke to improve your work. Each persona has:
- A specific **domain**: interrogating requirements, designing architecture, implementing against specs, breaking specs, evaluating output, scanning for anti-patterns, designing evaluations, capturing post-mortems.
- A **voice**: how it communicates (terse, skeptical, analytical, humble, etc.)
- **Operating procedures**: the steps it follows when invoked
- **Concrete examples**: actual prompts you can copy and run
- **Failure modes**: what goes wrong if the persona is misapplied

Personas are **tool-agnostic**. One neutral source of truth (`*.persona.md`) generates four outputs: Claude Code agents, skills, human cards, and portable JSON.

## The Two Families

### Spec-Driven Family

These personas guide the journey from a vague idea to a testable specification to implementation to verification.

| Persona | Role | Invoke When |
|---|---|---|
| **Interrogator** | Refuses to let an underspecified request become code | Your request is vague, or success criteria are unstated |
| **Architect** | Records only decisions that would cause incompatibility | Design requires trade-offs between valid approaches |
| **Implementer** | Works from acceptance criteria; test-first; terse | You have acceptance criteria and are ready to code |
| **Adversary** | Tries to break the spec before the code exists | You want to find gaps in a spec before implementation |

**Workflow**: Interrogator → Architect → Adversary → Interrogator (refine) → Implementer → Adversary (verify).

### Prompt-Upskilling Family

These personas improve the quality of work by evaluating it, checking for common pitfalls, designing measurements, and capturing lessons.

| Persona | Role | Invoke When |
|---|---|---|
| **Critic** | Scores output on five rubric dimensions (Precision, Helpfulness, Meaning, Immediacy, Trust) | You have output and want to know if it's ready |
| **Scanner** | Checks for seven anti-patterns (constant/variable confusion, import pollution, hardcoded vocabulary, dev text in user UI, non-functional UI, stale cache, overclaiming) | You want to check code for maintainability issues |
| **Eval Designer** | Turns "this feels better" into a measurement | You want to measure if something is actually better |
| **Scar Recorder** | Captures a lesson after something breaks | Something broke and you want to prevent it again |

**Workflow**: Build → Critic → Scanner (if code) → (if measuring improvements) Eval Designer. After incidents: Scar Recorder.

## Adding a Persona

1. Create a new file: `personas/<id>.persona.md`
2. Use the template below (copy from an existing persona)
3. Fill in the eight sections: Role, Voice, Operating procedure, Example prompts, Failure modes, plus frontmatter
4. Run `python export.py` to generate the exports
5. Run `python export.py --check` to verify
6. Commit both the source file and the generated exports

### Template

```yaml
---
id: <unique-id-in-kebab-case>
name: <Display Name>
family: spec-driven | prompt-upskilling
one_liner: <One sentence, starts with a verb>
invoke_when: <One sentence describing when to use this persona>
asks_for:
  - <thing>
  - <thing>
refuses:
  - <thing>
produces: <What you get back>
---

## Role

<Two paragraphs about what this persona does and why>

## Voice

<Describe how this persona communicates>

## Operating Procedure

<Numbered steps for how this persona works>

## Example Prompts

<At least three realistic examples of prompts you could paste>

## Failure Modes

<Three or four common mistakes, with fixes>
```

Each section should be 40–70 lines total.

## Running the Exporter

```bash
# Generate exports (creates export/ directory)
python personas/export.py

# Verify exports are current (used by CI)
python personas/export.py --check
```

The exporter:
- Parses all `*.persona.md` files (YAML frontmatter, no external deps)
- Generates four output targets from each persona:
  - **Claude agents** (`export/claude-agents/<id>.md`): System prompt for a subagent
  - **Claude skills** (`export/claude-skills/<id>/SKILL.md`): Slash-command skill definition
  - **Human cards** (`export/cards/<id>.md`): One-pager for tutorials
  - **Portable JSON** (`export/personas.json`): Machine-readable, for other tools
- Writes a header comment in each export warning against hand-editing

For details on what each export format is for, see [SURFACES.md](SURFACES.md).

## Persona Roster

| ID | Family | Name | One-Liner |
|---|---|---|---|
| `spec-interrogator` | spec-driven | The Interrogator | Refuses to let an underspecified request become code |
| `spec-architect` | spec-driven | The Architect | Records only decisions that would cause incompatibility |
| `spec-implementer` | spec-driven | The Implementer | Works from acceptance criteria; test-first |
| `spec-adversary` | spec-driven | The Adversary | Tries to break the spec before the code exists |
| `prompt-critic` | prompt-upskilling | The Critic | Scores output on five rubric dimensions |
| `anti-pattern-scanner` | prompt-upskilling | The Scanner | Checks work against seven anti-patterns |
| `eval-designer` | prompt-upskilling | The Eval Designer | Turns "this feels better" into a measurement |
| `scar-recorder` | prompt-upskilling | The Scar Recorder | Captures a lesson after something breaks |

## Using Personas in Claude Code

### As an Agent

```
/agent spec-interrogator
Help me understand what success looks like for this feature request.
```

Invokes the Interrogator as a subagent with its system prompt.

### As a Skill

```
/prompt-critic
Evaluate this API design — is it ready to ship?
```

Invokes the Critic with the skill definition.

### Directly

Paste the persona's voice and operating procedure into your system prompt:

```
You are the Interrogator. Your role is...
[copy Role, Voice, and Operating Procedure from the persona file]
```

## Using Personas Outside Claude Code

The `personas.json` export contains all persona metadata (frontmatter only, no body). Use it to build system prompts in any tool:

```python
import json

with open("export/personas.json") as f:
    personas = json.load(f)

for persona in personas:
    print(f"{persona['name']}: {persona['one_liner']}")
```

Then integrate the persona's role/voice/procedure into your system prompt for Cursor, Codex, or the raw Claude API.

## Related Documents

- [SURFACES.md](SURFACES.md): What is generated and where
- [../../README.md](../README.md): Harness documentation
- [../../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md): System design
- [../../tutorials/00-prompting/README.md](../tutorials/00-prompting/README.md): Prompting introduction
- [../../tutorials/30-skill-authoring/README.md](../tutorials/30-skill-authoring/README.md): Building skills

## Philosophy

Personas are **tool-neutral** because they outlive tools. The way to interrogate requirements, architect for compatibility, or evaluate quality doesn't depend on whether you're using Claude Code, Cursor, or the raw API. By writing the persona once and generating surface-specific forms, we ensure consistency and reduce maintenance burden.
