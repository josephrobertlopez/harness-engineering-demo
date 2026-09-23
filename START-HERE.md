# Start here

You have a zip. This gets you running in about two minutes, then points you
at the right document for whatever you actually came to do.

## 1. Check you can run it

Python **3.12 or newer**. That is the entire dependency list — no `pip
install`, no virtualenv, no network, no API key.

```bash
python --version
```

## 2. Run the test suite

```bash
python -m unittest discover -s tests -t .
```

Expect **83 tests, all passing, in under a minute**. If they pass, everything
in this repo works on your machine. If they don't, something is wrong with
the zip or your Python — nothing here depends on your environment beyond the
interpreter.

## 3. Watch the thing actually work

```bash
python -m wikiskill.cli --workspace ws --backend mock --decoy-iteration 3 run -k 8
```

Set `PYTHONPATH=src` first if you get an import error (`set PYTHONPATH=src`
on Windows cmd, `$env:PYTHONPATH="src"` in PowerShell, `export PYTHONPATH=src`
in bash).

You should see an agent's skills evolve, gated against a held-out split:

```
iter 1: train=0.00 val cand=0.20 inc=0.00 -> ACCEPT  R_best=0.20
iter 2: train=0.20 val cand=0.40 inc=0.20 -> ACCEPT  R_best=0.40
iter 3: train=0.40 val cand=0.40 inc=0.40 -> REJECT (no_improvement)  R_best=0.40
iter 4: train=0.40 val cand=0.60 inc=0.40 -> ACCEPT  R_best=0.60
iter 5: train=0.60 val cand=0.80 inc=0.60 -> ACCEPT  R_best=0.80
iter 6: train=0.80 val cand=1.00 inc=0.80 -> ACCEPT  R_best=1.00
```

That run is offline and deterministic — you will get those exact numbers.
Iteration 3 is a genuine rejection with a genuine rollback, not decoration.

Then look at what it produced:

```bash
python -m wikiskill.cli --workspace ws --backend mock show wiki
python -m wikiskill.cli --workspace ws --backend mock show skills
python -m wikiskill.cli --workspace ws --backend mock show impact
```

## 4. Learn something

Five tutorial tracks. Two are **graded** — you write something and the
harness scores it, offline. Full index: [tutorials/README.md](tutorials/README.md).

| Track | What you learn | Graded |
|---|---|---|
| [00 — Prompting, measured](tutorials/00-prompting/README.md) | What prompting can and cannot fix; the rubric; the seven anti-patterns | **yes** |
| [10 — Spec-driven development](tutorials/10-spec-driven/README.md) | BMAD: the spec as hub, two slicing routes, five personas | no |
| [20 — Compounding knowledge](tutorials/20-knowledge/README.md) | LLM Wiki: parallel research, credibility review, the edit rules | no |
| [30 — Skill authoring](tutorials/30-skill-authoring/README.md) | Write a skill, then measure whether it actually helped | **yes** |
| [40 — Harness engineering](tutorials/40-harness/README.md) | Three layers, the gate, rollback, resume | no |

Short on time? Do **00** then **30** — about 90 minutes, and they are the
two that end in a number rather than an opinion.

## 5. Reusable personas

[personas/](personas/README.md) holds eight role definitions in a
**tool-neutral** source format, generated into Claude Code subagents, Claude
Code skills, human-readable cards, and a portable JSON file. If your team
uses Codex or Cursor instead, read the JSON and build your own system prompt
from it — nothing here is locked to one tool.

## 6. Go where you need to

| You want to... | Read |
|---|---|
| Understand what the method *is* and why | [README.md](README.md) |
| See the numbers from a real model, and reproduce them | [docs/RESULTS.md](docs/RESULTS.md) |
| Look up a term | [docs/GLOSSARY.md](docs/GLOSSARY.md) |
| Find your way around the code | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Point it at **your own** tasks | [docs/EXTENDING.md](docs/EXTENDING.md) |
| Change the code without breaking it | [CLAUDE.md](CLAUDE.md) — invariants and scar tissue |
| Know what happened and when | [docs/COMMIT-HISTORY.md](docs/COMMIT-HISTORY.md) |

## A note on where this came from

This repo has **no git remote**. It was developed locally and handed over as
a zip. The `.git` directory is included, so `git log` works and full history
is preserved — see [docs/COMMIT-HISTORY.md](docs/COMMIT-HISTORY.md) for a
plain-text record in case you got a copy without it.

If you push it somewhere, you are the first person to do so; there is no
upstream to reconcile with.
