# Tutorials

Five tracks, grouped by their role in the argument the repo makes: that
knowledge compounds when **the thing you edit and the thing you read are
different objects** (see [the README](../README.md#the-same-shape-three-times)).

Two are **graded** — you write something and the harness scores it, offline.
Three are **guided**: real lessons, but they need a live agent, so there is
nothing honest to check without one.

They are independent. Start wherever your problem is.

### The pattern — two tools that already do this

Both are other people's MIT-licensed projects, credited in
[the README](../README.md#credits). These tracks are my reading of them,
not their documentation.

| Track | What you learn | Graded | Time |
|---|---|---|---|
| [20 — Compounding knowledge](20-knowledge/README.md) | LLM Wiki: immutable sources, derived articles, parallel research with independent credibility review | no | ~90 min |
| [10 — Spec-driven development](10-spec-driven/README.md) | BMAD: an append-only log, a derived spec, and why the two slicing routes must never be mixed | no | ~60 min |

### The mechanism — the same shape, made measurable

| Track | What you learn | Graded | Time |
|---|---|---|---|
| [40 — Harness engineering](40-harness/README.md) | Three layers, the gate, rollback, resume — and why the inference agent is structurally denied the wiki | no | ~60 min |

### The practice — doing it yourself, with a number at the end

| Track | What you learn | Graded | Time |
|---|---|---|---|
| [00 — Prompting, measured](00-prompting/README.md) | What prompting can and cannot fix; a five-dimension rubric; seven recurring failure patterns | **yes** | ~50 min |
| [30 — Skill authoring](30-skill-authoring/README.md) | Write a skill, measure whether it helped, avoid memorising the answer | **yes** | ~45 min |

## If you only have an hour

Do **00** then **30**. They are the two that end in a number rather than an
opinion, and together they teach the loop the rest of this repo automates:
measure, change one thing, measure again.

## Running the checks

```bash
python tutorials/check.py                        # every exercise
python tutorials/check.py 30-skill-authoring     # one track
python tutorials/check.py 00-prompting/01-diagnose  # one exercise
```

Everything runs offline against the `mock` backend. No API key, no network,
no install beyond Python 3.12+.

## What "graded" actually means

The mock backend recognises that your skill states a rule by matching
keywords — a stand-in for understanding it. That is enough to separate a
specific instruction from a vague one, and it is why these work with no API
key. It cannot tell a well-written skill from a merely correct one.

Treat a passing score as a floor, not a ceiling: failing means the
instruction is definitely unclear; passing does not mean it is good.

## Prerequisites by track

| Track | Needs |
|---|---|
| 00, 30 | Python 3.12+. That is all. |
| 10 | BMAD skills installed, `uv`, and `bmad setup` run in a project |
| 20 | LLM Wiki installed, plus `WebFetch`/`WebSearch` allowed in settings |
| 40 | Python 3.12+; read [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) first |
