# The `/fidelity:*` commands

Lesson 3's prompts as Claude Code slash commands. `start.py` copies every
`.md` file here, except this README, into a workspace's
`.claude/commands/fidelity/`, filling in three placeholders:

| placeholder | becomes |
|---|---|
| `{{PYTHON}}` | the interpreter that ran `start.py` (the venv's, via `setup.py --install`) |
| `{{JUDGE}}` | the absolute path to `spec_fidelity.py` |
| `{{VAGUE_TERMS}}` | the ticket's vague words, from the exercise's `rubric.json` |

| command | step | writes |
|---|---|---|
| `/fidelity:interrogate [answers]` | 1 | `interview.md`, append-only |
| `/fidelity:prd` | 2 | `prd.md`, then judges it |
| `/fidelity:review-prd` | 2b | nothing; adversarial review |
| `/fidelity:propose <change-id>` | 3 | `openspec/changes/<id>/` |
| `/fidelity:build` | 4 | `impl/`, test-first |
| `/fidelity:judge` | any | nothing; explains each finding |
| `/fidelity:enforce` | 5 | nothing; the agent half, via the plugin if installed |

Rules for editing them, each learned the hard way:

- **A `!` shell line must pass `--exit-zero` to the judge.** Claude Code
  aborts a command whose `!` line exits non-zero, so a command meant to
  explain the judge's failures would never see them. A test enforces this.
- **Never name a stakeholder fact.** The prompts are copied into the
  workspace; a test fails if any fact from any rubric is readable there.
- **Say what to do when the judge reports a gap.** The PRD command tells
  the model to go back to the product owner rather than invent an answer,
  and a Haiku trial showed it follows that.
