# Lesson 1 — Three layers

## The separation

Experience is split into three layers on disk, and the loop stitches them
together in a specific order.

```
workspace/
  raw/                 immutable execution traces
  wiki/                compounding patterns
  skills/              executable procedures
```

Each layer is written only by one kind of agent, and each is read by the next.

| Layer | Writer | Reader | What it holds |
|---|---|---|---|
| `raw/` | Inference Agent | Wiki Maintainer | traces of failures and successes |
| `wiki/` | Wiki Maintainer | Skill Proposer | patterns that explain the failures |
| `skills/` | Skill Proposer | Inference Agent | the rules the next iteration will use |

There is one more directory, `.state/`, but **it is not one of the paper's
three layers** — it is harness bookkeeping: the journal that makes resume work,
the content-addressed snapshots that make rollback work, and the response cache
that makes resume cheap.

## The asymmetry that matters

**The wiki is never rolled back.**

When the Inference Agent runs iteration 4, suppose it produces a trace that
contradicts a pattern from iteration 2. The wiki entry stays. The pattern was
rooted in real failure data; rejecting the skill does not un-root it.

That asymmetry is the mechanism by which knowledge compounds:
- Iteration 2 fails on timestamps, the maintainer documents `iso_z`, the
  proposer writes a skill, the gate accepts it.
- Iteration 3 proposes a skill for rounding, the gate rejects it (false
  positive on validation). The wiki entry for rounding stays, even though the
  skill is deleted.
- Iteration 4 proposes a better rounding skill. It passes. The earlier failed
  attempt was not wasted — the pattern it was built on compounds into the next
  proposal.

Skills are disposable. Patterns are permanent. That difference is where the
method's power lives.

## What .state/ is

Skip this on first read — it is bookkeeping details.

```
.state/
  HEAD.json                     pointer to the current skill set
  journal.jsonl                 per-phase log, one JSON line per entry
  skillsets/<sha>/              immutable content-addressed skill snapshots
  llmcache/<sha>.json           response cache, keyed by request hash
```

The journal is the load-bearing piece. Each phase writes its completion to
`journal.jsonl` *before* doing anything irreversible. On resume, the loop
replays from the first phase that never wrote its journal entry. That is how
a crash at any point restarts to exactly the same place.

The skill snapshots are how rollback works: there is no undo path because
there is nothing to undo. The candidate lives in its own snapshot; rejection
simply never points `HEAD.json` at it. If you never move `HEAD`, you never
have a rollback bug.

---

Next: [Lesson 2 — Inference isolation](lesson-02-inference-isolation.md)
