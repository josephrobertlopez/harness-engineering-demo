# Lesson 1 — Fidelity, and why the ticket is the environment

## The claim this track is built on

The ai-literacy-superpowers plugin puts it bluntly: *every AI failure is an
environment problem.* An assistant that ignores your logging convention
never saw it. An assistant that builds "a chatbot that doesn't say anything
bad" by adding one line to a system prompt did what the ticket said; the
ticket just did not say anything checkable.

Here is SUP-88's whole safety requirement:

> not say anything bad

Hand that to Claude and you get *a* chatbot. Whether it is the chatbot
support needed depends on things the ticket never states. Should the bot
refuse a pasted card number before the model sees it? Should that card
number stay out of the conversation history? Is "bad" about tone,
hallucinated refund policies, or data leaving the building? The model did
not fail to care about those. They were not in its environment.

So the work in this track is mostly not coding. It is **changing the
environment until the code has only one reasonable shape** — then checking
that the code took it.

## Fidelity, defined narrowly

*Fidelity* here means each artifact preserves the one before it, and adds
nothing the one before it did not ask for:

| arrow | faithful when | the failure it catches |
|---|---|---|
| ticket → PRD | every vague word is replaced by the behaviour it stood for | "fast" survives into the PRD and becomes whatever the implementer guessed |
| PRD → spec | every `PRD-n` is traced by a requirement, and every requirement traces to a `PRD-n` | a requirement silently dropped; a feature nobody asked for |
| spec → tests | every `#### Scenario:` is named by a test, and every test names a real scenario | an untested scenario; a test for a scenario that was edited away |
| tests → code | the tests pass, and each test asserts what its scenario's THEN says | green tests that prove less than they claim |

The first three rows are **structural**: a script can check them without
understanding anything. The last is **semantic**: it needs a reader. That
split is the whole design of the judge.

## Where the two halves live

Each exercise has a `HARNESS.md`, in the format the plugin's
`harness-enforcer` agent reads. Its constraints come in three kinds, and the
kind is the point:

```markdown
### Every scenario is tested, and tests pass
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage build`

### Spec captures intent
- **Enforcement**: agent
- **Tool**: harness-enforcer

### Image actually runs
- **Enforcement**: unverified
- **Tool**: none yet -- needs a Docker daemon
```

- **deterministic** — a command; exit code 0 passes. Cheap, fast,
  authoritative. Runs on every commit.
- **agent** — the `harness-enforcer` reads the rule and the code and
  reports findings with `file:line`. Slower, costs tokens, catches meaning.
- **unverified** — declared intent with no automation yet. Honest about the
  gap instead of pretending it is covered. The plugin calls moving a
  constraint up this ladder *promotion* (`/harness-constrain`).

A constraint you would like to be deterministic but cannot yet make
deterministic belongs in `agent`, not in a prompt. A constraint nothing
checks belongs in `unverified`, so it is at least written down.

## Why the trace IDs are worth the noise

Every requirement in the PRD gets an ID (`PRD-3`). Every requirement in the
OpenSpec delta carries a `Trace: PRD-3` line. Every test's docstring carries
`Scenario: <exact name>`. It looks bureaucratic. It is what turns "is this
faithful?" from an opinion into a set difference:

```
PRD ids       − traced ids       = dropped requirements
traced ids    − PRD ids          = invented requirements
scenario names − test tags       = untested behaviour
test tags     − scenario names   = stale or invented tests
```

(The first subtraction has a loophole: fold PRD-7 into another
requirement's `Trace: PRD-1, PRD-7` and delete PRD-7's own requirement, and
the set difference is empty. The judge closes it by requiring every PRD id
to have a requirement of its own. An adversarial review found it; lesson 4
lets you try it.)

Four subtractions, each one a class of drift that otherwise shows up months
later as "why does it do that?". OpenSpec itself does not ask for
`Trace:` lines; that convention is this track's, layered on top.

## What you should take from this lesson

- The ticket is part of the environment the model works in. Improve it
  before you prompt against it.
- Split every quality you care about into the part a script can check and
  the part that needs a reader, and put each where it belongs.
- Traceability is what makes fidelity a subtraction rather than a debate.

---

Next: [Lesson 2 — OpenSpec in ten minutes](lesson-02-openspec.md)
