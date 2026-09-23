# Track 10 — Spec-driven development with BMAD

> **About this track.** [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD)
> is an MIT-licensed project by bmad-code-org. This track is **my reading of
> it, not its documentation** — it is opinionated, it sometimes disagrees
> with how the project presents itself, and it will drift as the upstream
> changes. Go to the source for anything authoritative.
>
> It is here because BMAD independently arrives at the pattern this repo is
> about: an append-only log (`.memlog.md`) that a contract (`SPEC.md`) is
> *derived* from, never hand-merged. See
> [the README](../../README.md#the-same-shape-three-times).


**~90 minutes. Requires a project with `_bmad/` and `uv` installed.**

BMAD is **hub-and-spoke**, not a pipeline. The spec is the hub. All analysis
and planning skills exist to feed it; they run in any order because `SPEC.md`
is derived from an append-only log, never hand-merged.

This is the opposite of the older v6 "epics route" (brief → PRD → architecture
→ epics), which is still available but not the default. **Presenting both as
a required sequence teaches the anti-pattern.** This track does not.

## Prerequisites

- Python 3.12+
- `uv` (0.12.5 or higher) installed and on your PATH
- You have run `python -m unittest discover -s tests -t .` from the repo root
  and it passed

## What you will build

A BMAD-driven workflow for a real change. You will see: the spec hub in
action; the difference between the ticketing route and the epics route; when
to use each; why you never mix them; and the menu of feeders that populate
the spec.

## Lessons

| # | Lesson | Time |
|---|---|---|
| 1 | [Setup — `bmad setup` and the `_bmad/` folder](lesson-01-setup.md) | 10 min |
| 2 | [Hello world — `bmad-build` alone, no planning](lesson-02-hello-world.md) | 15 min |
| 3 | [The spec hub — SPEC.md structure and the `.memlog.md`](lesson-03-spec-hub.md) | 20 min |
| 4 | [Two slicing routes — ticketing vs epics, never both](lesson-04-two-routes.md) | 25 min |
| 5 | [Feeders and personas — the menu, and who uses what](lesson-05-feeders-personas.md) | 20 min |

## Traps: things that look right and aren't

**1. The linear sequence is not required.**
A common first mistake: installing BMAD, reading a blog post about the full
workflow, and running every skill in order. The corpus is explicit: *"They are
not a mandatory sequence to complete."* Start with the spec hub (lesson 3)
and pull in only the skills that fit your problem.

**2. Never mix slicing routes.**
The spec/ticketing route and the v6 epics route are incompatible. Ticketing
works with a spec alone; epics requires both a PRD *and* an architecture
document. Use one per piece of work. `bmad-correct-course` enforces this: it
halts if it sees a spec with epics or an epics file without both a PRD and
architecture.

**3. `bmad-sprint-planning` reads only `epics.md`.**
If you took the ticketing route, sprint planning does nothing — there is
nothing for it to read. It is not a bug, it is evidence you chose the wrong
route.

**4. Agent menu codes collide.**
`CR` is "competitive research" for Mary (the analyst), "code review" for
Amelia (the engineer). Learn which agent is being invoked by the command and
which code applies.

**5. Artifacts are snapshots, not living docs.**
Once an artifact (prd.md, architecture.md, epics.md) is built, archive it if
you are keeping it as reference. Agents see old artifacts and treat them as
source of truth, creating silent failures: you change the idea, the old
document contradicts it, and the agent follows the document.

**6. Deprecated skill names still resolve.**
Old blog posts name `bmad-create-prd` and `bmad-market-research`. These are
forwarders to the new names (`bmad-prd`, `bmad-deep-recon`) and still work,
which means a typo can hide for months.

## Where to find real output

The fastest way to see what these artifacts look like is to generate them.
Run lesson 2 against a small change in a repo you already have; `bmad spec`
writes a spec folder you can read in a couple of minutes.

Reading someone else's `prd.md` teaches less than watching your own get
written, because the interesting part is the questions it asks you.

---

Next: [Lesson 1 — Setup](lesson-01-setup.md)
