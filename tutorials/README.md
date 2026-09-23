# Tutorials

Five tracks. Two are **graded** — you write something and the harness scores
it. Three are **guided** — real lessons, but they need a live agent, so
there is nothing to check offline.

Start with whichever one matches the problem you have. They are independent;
only 00 and 30 reference each other.

| Track | What you learn | Graded | Time |
|---|---|---|---|
| [00 — Prompting, measured](00-prompting/README.md) | What prompting can and cannot fix; rubric scoring; the seven anti-patterns; specificity | **yes** | ~50 min |
| [10 — Spec-driven development](10-spec-driven/README.md) | BMAD: the spec as hub, the two slicing routes, the five personas | no | ~60 min |
| [20 — Compounding knowledge](20-knowledge/README.md) | LLM Wiki: parallel research, credibility review, the three-tier edit rule | no | ~90 min |
| [30 — Skill authoring](30-skill-authoring/README.md) | Write a skill, measure whether it helped, avoid memorising | **yes** | ~45 min |
| [40 — Harness engineering](40-harness/README.md) | The three layers, the gate, rollback, resume | no | ~60 min |

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
