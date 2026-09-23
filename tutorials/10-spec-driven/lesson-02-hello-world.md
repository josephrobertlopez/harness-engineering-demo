# Lesson 2 — Hello world: `bmad-build` alone, no planning

## The minimum viable loop

The minimum loop is: make the change, verify it works. Planning is optional.

From the routing doc: *"Obvious and low-risk (typo, formatting, config): just
make the edit. No skill."* For changes that are slightly less obvious but
still small and isolated, `bmad-build` alone is the right call.

`bmad-build` needs one thing: a spec. You do not write it by hand.

## Feed the spec once

Take any input — an idea, a brain dump, a Slack thread, a partial PRD, even
an existing design doc you want to refactor. Paste it into `bmad-spec`:

```bash
bmad-spec
```

The skill will prompt you for input. Paste your text, end with EOF (Ctrl-D on
Unix, Ctrl-Z then Enter on Windows), and it derives `SPEC.md` into
`_bmad/spec/SPEC.md`.

Never edit `SPEC.md` by hand. It is derived from an append-only log
(`.memlog.md`) and a hand edit is silently overwritten on the next derive.

### What goes into the spec

Anything, really. Very large inputs are worth splitting rather than pasting
whole — the skill does not document a hard ceiling, so treat that as caution
rather than a known limit. Input that is
too thin ("an app for hikers") bounces to `bmad-product-brief`. But a
brain dump, a Slack thread, a partial brief, or even a transcript all work.

## Now build

```bash
bmad-build
```

The skill reads `SPEC.md`, decides what to build, and builds it. Output is
in your repo and ready to test.

## The decision rule for "do I need planning?"

Ask: **will the work be built by one person, or will it fork?**

| scenario | answer | route |
|---|---|---|
| One engineer, isolated change, I can visualize the whole thing | one person | `bmad-build` only |
| Two teams choosing incompatibly (DB schema, API contract, deployment) | will fork | get an `architecture.md` first, then build |
| Large surface, competitive review needed, or I need to socialize the idea | complex | run feeders, fill the spec, then build |

Most work is the first: one engineer, one repo, small change. `bmad-build`
alone is the right call. Do not add skills until you need them.

## What `bmad-build` outputs

- Changed files in your repo (ready to review, test, commit)
- `_bmad/build-log.md` — what the skill decided and why
- No database updates, no tickets created (that comes in lesson 4)

The change is **your responsibility to test**. The skill is not a test runner.

## Why not always use planning?

Running `bmad-spec` + `bmad-build` takes 2–3 minutes (fast), but running the
full spec → ticketing workflow takes 8–15 minutes. Running analysis feeders
(competitive research, product brief, architecture) adds another 10–20
minutes each. **If you do not need it, you are burning user time for no
return.**

The rule is simple: call `bmad-spec` first. If the spec satisfies you, call
`bmad-build` alone. Only add planning skills if the spec does not capture
enough of the picture.

---

Next: [Lesson 3 — The spec hub](lesson-03-spec-hub.md)
