# Architecture

A map of the code. For *why* each constraint exists, read
[../CLAUDE.md](../CLAUDE.md) — this file is the "where is everything".

## One screen of orientation

The method separates agent experience into three layers that live on disk,
and runs a loop that turns the first into the second into the third.

```
   tasks ──► Inference Agent ──► raw/          immutable traces
                  ▲                │
                  │                ▼
                  │          Wiki Maintainer ──► wiki/patterns/   compounding
                  │                │                              knowledge
                  │                ▼
                  │           Skill Proposer   (reads wiki, never inference)
                  │                │
                  │                ▼
                  │              Gate ──► accept? move HEAD : do nothing
                  │                │
                  └──── skills/ ◄──┘        executable procedures
```

The arrow that is **missing** is the point: nothing goes from `wiki/` to the
Inference Agent. That isolation is the paper's central ablation.

## Module map

| Module | Responsibility |
|---|---|
| `types.py` | Every dataclass that crosses a disk or LLM boundary. Imports nothing from the package except `util`. |
| `util.py` | Atomic writes, LF normalisation, content hashing, path-traversal guard. Everything else uses these rather than touching the filesystem directly. |
| `config.py` | `RunConfig`, workspace `Paths`, and `MODEL_CAPS` — the per-model request-shape table. |
| `protocol.py` | Parsers for the `THOUGHT:` / `ACTION:` / `ANSWER:` text protocol and fenced JSON blocks. |
| `patching.py` | Pure validation + application of wiki patches over an in-memory page map. All-or-nothing. |
| `gating.py` | The accept/reject decision (the paper's Eq. 4) and the skill byte-budget check. |
| `loop.py` | `Workspace`, `Journal`, `Evaluator` (parallel), and `EvolutionLoop` — the seven-phase orchestrator. |
| `report.py` / `cli.py` | Command line surface. |

### `layers/` — the only code allowed to write `workspace/`

| Module | Owns | Notable constraint |
|---|---|---|
| `raw.py` | `workspace/raw/` | Append-only. A `.trace.json` existing *is* the completion marker for resume. Paths are bucketed by skill-set sha so incumbent and candidate rollouts of the same task cannot collide. |
| `wiki.py` | `workspace/wiki/` | **No delete API exists.** Writes are `apply_patch_ops`, `append_log`, `append_skill_impact` — that is the whole surface. |
| `skills.py` | `workspace/skills/` + `.state/` | Content-addressed immutable snapshots behind one atomic `HEAD.json`. `skills/` is a human-readable mirror that no code reads. |

### `agents/` — the three roles

| Module | Sees | Does not see |
|---|---|---|
| `inference.py` | the skill set, the environment | **the wiki** (no handle, no import) |
| `maintainer.py` | sampled traces, the pattern index | — |
| `proposer.py` | pattern index, impact ledger, outcome counts; full pages via `read_file` | — |

### `backends/` — one narrow interface

`complete(LLMRequest) -> LLMResponse`: a system prompt and one rendered
prompt string in, text out. Deliberately narrow, because the default backend
shells out to `claude -p`, which is single-shot and takes no custom tool
schemas — so tool use is a *text protocol* the harness parses, identical
across all three backends.

| Backend | Notes |
|---|---|
| `mock.py` | Deterministic and **skill-sensitive** — it answers correctly only if the injected skills cover the task's quirk. That is what lets the offline test assert real learning. |
| `claude_cli.py` | Default. Reuses the Claude Code login, no API key. Four isolation flags matter; see the file's docstring. |
| `anthropic_api.py` | The SDK. Branches on `MODEL_CAPS` because Opus 5 / Sonnet 5 and Haiku 4.5 take incompatible thinking parameters. |
| `base.py` | The protocol plus `CachingBackend`, a content-addressed response cache — this is what makes `--resume` cheap. |

## The seven phases

Each is idempotent, and they run in this order:

```
rollout_train → wiki_update → propose → apply_candidate
              → eval_val → gate_decision → commit
```

The invariant holding it together is **decide, journal, then act**. Moving
`HEAD` is the only irreversible step in the loop and it happens strictly
after the decision justifying it is durable in `.state/journal.jsonl`. That
is why a crash mid-iteration resumes to exactly the same place — asserted by
`tests/test_resume.py`, which is the highest-value test in the suite.

## Where state lives

```
workspace/
  raw/iter-NN/{split}/{sha8}/{task}.trace.json   immutable evidence
  wiki/patterns/*.md, logs.md, skill-impact.md   never rolled back
  skills/<name>/{SKILL.md,PURPOSE.md}            mirror of HEAD
  .state/HEAD.json                               the atomic pointer
  .state/journal.jsonl                           phase log, drives resume
  .state/skillsets/<sha>/                        immutable snapshots
  .state/llmcache/<sha>.json                     response cache
```

`.state/` is **not** one of the paper's layers. It is harness bookkeeping.
