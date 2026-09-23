# Lesson 4 — Rollback and resume

## Seven phases, each idempotent

The loop runs the same sequence every iteration:

```
rollout_train → wiki_update → propose → apply_candidate
              → eval_val → gate_decision → commit
```

Open `src/wikiskill/loop.py` and search for `PHASES =`. You will see:

```python
PHASES = (
    "rollout_train",
    "wiki_update",
    "propose",
    "apply_candidate",
    "eval_val",
    "gate_decision",
    "commit",
)
```

Each phase is idempotent — running it twice produces the same result as
running it once. That property is what makes resume work: if a crash happens
in the middle of phase 3, restarting simply re-runs phase 3 from the
beginning.

## The journal — decide, journal, then act

Before anything irreversible happens, the phase writes its completion to
`journal.jsonl`:

```python
def record(self, iteration: int, phase: str, data: dict | None = None) -> None:
    append_text(
        self.path,
        canonical_json({"iter": iteration, "phase": phase, "data": data or {}}) + "\n",
    )
```

This is the invariant that makes resume survivable: **decide, journal, then act.**

The decision to accept or reject is made, validated, and *durable* (written to
disk) before `HEAD.json` is ever touched. If a crash happens between writing
the journal entry and moving `HEAD`, the journaled decision is still there
when the process restarts. The loop replays from the first phase that has no
journal entry, and arrives at exactly the same place.

## Resume starts from the first uncommitted iteration

The naive restart is to resume from the last journal entry:

```python
last_entry_iter = max(e["iter"] for e in journal.entries())
resume_from = last_entry_iter + 1
```

This is **wrong**. A crash partway through iteration 5 leaves iterations 1–4
with complete journal entries and iteration 5 with partial ones. Restarting at
iteration 6 silently produces a shorter history than an uninterrupted run.

Instead, resume is keyed off the last iteration that reached the `commit` phase:

```python
def last_committed(self) -> int:
    """Highest iteration that reached its commit phase."""
    return max(
        (e["iter"] for e in self.entries() if e["phase"] == "commit"),
        default=0,
    )
```

A crash mid-iteration 5 leaves `last_committed() == 4`, so resume starts at 5
and produces the correct history.

## Rollback is not implemented because there is nothing to undo

A skill set is immutable and content-addressed. The snapshots live in
`.state/skillsets/<sha>/`, and `HEAD.json` is a pointer file:

```json
{"sha": "abc12345"}
```

When the Skill Proposer creates a new candidate, it writes to a fresh snapshot
with a new sha. Validation runs both incumbent (under the old sha) and
candidate (under the new sha). The gate decides which one HEAD should point at.

If the candidate fails, `HEAD.json` is simply never updated. There is no undo
path because there is no change to undo. The candidate sits in its snapshot
forever, unreferenced, and is garbage-collected later if needed.

This design eliminates a whole class of bugs: **undo paths can be wrong.** By
not having one, there is no way to get it wrong.

## The one place rollback matters: the wiki is never rolled back

Skill snapshots are ephemeral. The wiki is permanent.

When the gate rejects a skill proposal, the patterns that motivated it stay in
`wiki/`. This is the asymmetry from Lesson 1: knowledge lives longer than the
skills built from it.

---

## Seeing it in action

Read the test suite. `tests/test_resume.py` exercises a crash partway through
an iteration and verifies the resumed run arrives at the same place. It is the
highest-value test in the repo because resume is where most of the subtle bugs
live.

Next: Read the source. Start with `src/wikiskill/loop.py`, then trace into
`layers/raw.py`, `layers/wiki.py`, and `layers/skills.py`. Each layer owns
exactly one directory and enforces its invariants at the seam.

---

That covers the harness. The exit ramp is `docs/EXTENDING.md` — the seam for
swapping in your own benchmark.
