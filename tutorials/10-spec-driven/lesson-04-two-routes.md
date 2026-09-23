# Lesson 4 — Two slicing routes: spec/ticketing vs epics, never both

## Two ways to carve up work

After you have a spec, there are two paths to slice the work into tickets or
epics:

| aspect | spec/ticketing | v6 epics |
|---|---|---|
| input | SPEC.md alone | PRD + architecture doc (no spec needed) |
| tickets | `bmad-preview-ticketing` | not created by skill (manual or Jira export) |
| epics | not created | `bmad-create-epics-and-stories` |
| planning | `bmad-preview-ticketing` (optional preview) | `bmad-sprint-planning` (reads epics.md) |
| skill effort | medium | high |
| when to use | most of the time | when you have both PRD and architecture already |

**Golden rule: use one per piece of work, never both.**

## The spec/ticketing route (most common)

You have a spec. You want to break it into tickets.

```bash
bmad-preview-ticketing
```

The skill:
- Reads `SPEC.md`
- Sizes each capability at intake (S, M, L, XL)
- Generates a preview of tickets grouped by size and risk
- Outputs to `_bmad/tickets-preview.md`

The preview shows what the tickets *would* look like. It is **not** written
to your ticket system yet — `bmad-build` does not manage ticket status.

This route is lightweight: a single skill, one run, output you review and
can manually copy to Jira or Linear. It works because the spec captures the
intent and success conditions.

## The v6 epics route (when you already have structure)

You already have a PRD and an architecture document (from an earlier phase,
or from a different tool). You want to break work into epics and stories.

Hard requirement: you must have **both**:
- `prd.md` (a product requirements document)
- `architecture.md` (a system design document)

A spec is *not* a substitute. If you have a spec but no PRD, you do not have
enough structure for this route.

```bash
bmad-create-epics-and-stories
```

The skill:
- Reads `prd.md` and `architecture.md`
- Creates epics.md with high-level work items
- Creates stories.md with detailed acceptance criteria

Then:

```bash
bmad-sprint-planning
```

Reads `epics.md` and assigns work to sprints.

This route is heavyweight: two skills, structured input, high effort, but
suitable for larger initiatives where the PRD and architecture have already
been socialized and approved.

## The enforcement: `bmad-correct-course`

If you mix the routes — a spec with epics, or trying epics without a PRD —
`bmad-correct-course` halts and tells you which route you are in:

```
ERROR: mixing routes.
You have: SPEC.md + epics.md
Pick one: (spec/ticketing) OR (prd + architecture + epics/epics-route)
```

There is no override. The constraint is enforced because mixing routes creates
silent failures: the spec says one thing, the PRD says another, and agents
follow whichever they see first.

## Why never both?

The spec is derived; the PRD is hand-written. They can diverge, and when they
do, no skill can know which one is correct. `bmad-correct-course` prevents
the confusion by requiring you to pick one path.

For most work: **spec/ticketing is the right call.** It is faster, uses the
hub-and-spoke derivation model, and does not require a PRD. Use epics only
if you already have both a PRD and architecture document and you are managing
a complex multi-team initiative.

## What happens in `bmad-sprint-planning`

If you took the spec/ticketing route:

```bash
bmad-sprint-planning
```

Does nothing. It reads `epics.md` and finds nothing to plan. This is not a
bug — it is evidence you chose the right route. Do not treat it as a missing
step.

If you are on the epics route, `bmad-sprint-planning` reads your epics,
considers velocity and team capacity, and breaks them into sprints with
assigned owners.

---

Next: [Lesson 5 — Feeders and personas](lesson-05-feeders-personas.md)
