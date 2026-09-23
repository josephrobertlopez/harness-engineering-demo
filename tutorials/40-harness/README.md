# Track 40 — The harness and the loop

**~60 minutes. No code to write. Read the implementation, understand the constraints.**

This track explains how the WikiSkill paper becomes runnable code. It covers
the three-layer architecture, why the Inference Agent is structurally isolated
from the wiki, how the validation gate works, and how rollback and resume are
built without traditional undo.

## Prerequisites

- You have read the main `README.md` and `CLAUDE.md` in the repo root
- You have run `python -m unittest discover -s tests -t .` from the repo root
- Skim `docs/ARCHITECTURE.md` so you know where the code lives

## What you will understand by the end

- Why knowledge compounds even when a skill fails — the wiki's asymmetry
- How a structural guarantee (no import, no parameter) beats a prompt instruction
- The accept/reject decision and why paired re-measurement matters
- How seven idempotent phases survive a crash and resume correctly

## Lessons

| # | Lesson | Time |
|---|---|---|
| 1 | [Three layers](lesson-01-three-layers.md) — raw traces, wiki patterns, executable skills | 15 min |
| 2 | [Inference isolation](lesson-02-inference-isolation.md) — why the agent cannot see the wiki | 15 min |
| 3 | [The gate](lesson-03-the-gate.md) — validation, decision, rollback | 15 min |
| 4 | [Rollback and resume](lesson-04-rollback-resume.md) — journaled phases, atomic moves, no undo | 15 min |

## Checking your work

This track has no exercises. Read the lessons, then read the code they point at.
