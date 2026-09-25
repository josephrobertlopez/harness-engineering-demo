# Trial: track 50 with Claude Haiku 4.5 — 2026-09-25

The evidence behind the "Tested with Haiku" section of
[track 50's README](../../tutorials/50-spec-fidelity/README.md#tested-with-haiku).
This branch is a record, not something to merge.

## Setup

- **Developer:** `claude-haiku-4-5` in Claude Code, one session per
  exercise, driven only through the `/fidelity:*` slash commands that
  `start.py` installs — the same commands a learner types.
- **Product owner:** a second `claude-haiku-4-5`, no tools, given only
  `stakeholder-answers.md` and told to answer only what was asked.
- **Workspace:** made by `start.py`; the stakeholder file was then moved
  out of the developer's reach.
- **Audit:** every tool call logged (`tool-calls.md`); none touched a
  stakeholder file, a rubric or a `solution/` folder.
- **Script:** [`run_trial.py`](run_trial.py). Machine paths in the record
  are rewritten to `<ws>` (the workspace) and `<repo>` by
  [`scrub.py`](scrub.py).

## Runs

| folder | exercise | judge | dev cost | notes |
|---|---|---|---|---|
| `workspace/ops-1432` | 01 Docker REST | 3/3 | $1.94 | image works; HEAD answered 501 (rubric since tightened) |
| `workspace/sup-88` | 02 LangChain chatbot | 3/3 | $1.69 | refusal edge cases all correct |
| `workspace/devx-311-attempt-1` | 03 MCP | 0/3 | $1.56 | Haiku's correct question never reached the PO — harness bug |
| `workspace/devx-311-attempt-2` | 03 MCP | 3/3 | $1.83 | unusable by any MCP client: replies had no `id` |
| `workspace/devx-311-attempt-3` | 03 MCP | 3/3 | $1.33 | Claude Code refused it: no `capabilities` in `initialize` |
| `workspace/devx-311-attempt-4` | 03 MCP | 3/3 | $1.76 | connects in Claude Code and the SDK client; accepts `limit: 99` and an unlisted argument |

Each folder has `interview.md` (the append-only Q&A), `prd.md`, the
OpenSpec change, `impl/`, `judge.txt` (the deterministic judge at the time
of the run), `steps.json` (every command and reply) and `tool-calls.md`.

The judge reports are from the judge *as it was when the run happened*.
Attempts 2, 3 and 4 are green there and fail the current judge — that is the
point of keeping them.

## The real harness-enforcer

After the Haiku runs, the ai-literacy-superpowers plugin (0.92.0) was
installed and its own `harness-enforcer` agent run on `claude-sonnet-5`
with the prompt from lesson 3, step 5. Its verdicts, verbatim:

| file | workspace | verdict | cost |
|---|---|---|---|
| [`enforcer/A.md`](enforcer/A.md) | exercise 1 reference solution | 5/5 pass | $0.62 |
| [`enforcer/B.md`](enforcer/B.md) | the same, plus a `/currencies` endpoint (lesson 4, step f) | No gold-plating: FAIL | $0.55 |
| [`enforcer/C.md`](enforcer/C.md) | `workspace/devx-311-attempt-4` | 3 of 6 fail, including a flag injection that writes files | $0.79 |

The flag injection in C was confirmed by hand and is now a deterministic
probe in the judge.
