# Lesson 3 — The spec hub: SPEC.md structure and the `.memlog.md`

## Why the spec is the hub

BMAD is hub-and-spoke: the spec is the center, and every skill that produces
analysis (Mary's competitive research, Winston's architecture work, UX
review, etc.) exists to feed it. The spec is *re-derived* from an append-only
log instead of hand-merged, so feeders can run in any order and there is a
single point of truth.

This is the inversion of the older v6 pipeline (brief → PRD → epics →
implementation), where you had to run every step in sequence. Here: feed the
hub once, then pull in the skills you actually need.

## SPEC.md structure

`SPEC.md` (in `_bmad/spec/`) has five sections:

```markdown
# Spec: [Title]

## Why

[The problem statement, the gap, the reason we do this work. One paragraph.]

## Capabilities

### CAP-1: [capability name]

**Intent:** [What does the user want?]

**Success condition:** [How do we know it worked?]

[Other details as needed.]

### CAP-2: [next capability]

[Same structure...]

## Constraints

[Hard limits: must run on X, must integrate with Y, compliance requirement Z.]

## Non-goals

[What we explicitly do not do. Prevents scope creep.]

## Success signal

[How we measure if the whole thing worked. One metric or dashboard, measurable.]
```

Each capability gets a stable `CAP-N` ID. These IDs persist even when the
description changes, so you can reference them in tickets and commit messages
without them going stale.

## The `.memlog.md` is the source of truth

You never edit `SPEC.md` by hand. Instead, feeders and `bmad-spec` itself
append to `_bmad/spec/.memlog.md` — a log of all the input that went into
the spec.

`SPEC.md` is *derived* from the memlog. When you run `bmad-spec` again to
feed in new input, it:

1. Appends your new input to `.memlog.md`
2. Re-derives the entire `SPEC.md` from the log
3. Commits the change

A hand-edit to `SPEC.md` is overwritten on the next derive. This is not a
bug; it is the feature that lets feeders work in any order.

## Feeding the spec is append-only

Once you say something to `bmad-spec`, it stays in the memlog. If you change
your mind, you append a new statement that supersedes the old one. The full
history is preserved.

Example:

```markdown
## Input 1: Initial brain dump

"We need faster search. Current Elasticsearch query takes 3s."

## Input 2: Winston's architecture work

"Competitive research shows Redis for caching. We should add Redis to the
stack."

## Input 3: Overriding CAP-1

"On second thought, CAP-1 (Elasticsearch tuning) is not the right direction.
Archive it. Do Redis instead."
```

The spec is re-derived after each append, and archived capabilities stay
archived even if new input references them.

## No "merge conflicts"

Because the memlog is append-only and the spec is derived (not hand-edited),
two feeders can run in parallel. When they both write to the memlog, the
appends combine and the spec re-derives cleanly. No merge conflicts, no
lost work.

(This is the core reason the method is hub-and-spoke, not a pipeline.)

## When to call `bmad-spec` again

- You have new input (a feeder's output, a Slack conversation, a conference
  talk you want to incorporate)
- You want to override or adjust something
- You are starting a new phase (analysis done, time to plan; planning done,
  time to build)

Each call appends, re-derives, and commits.

---

Next: [Lesson 4 — Two slicing routes](lesson-04-two-routes.md)
