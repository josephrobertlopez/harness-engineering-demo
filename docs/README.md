# docs

Reference documents for the WikiSkill harness. Start with
[../README.md](../README.md) for what the method is and
[../CLAUDE.md](../CLAUDE.md) for the invariants you must not break. The
files here answer narrower questions.

## Index

**[ARCHITECTURE.md](ARCHITECTURE.md)** -- Where is everything? A module map
of `src/wikiskill/`, which layer owns which part of `workspace/`, what each
agent can and cannot see, the seven phases in order, and where state lives
on disk. It covers the "where"; CLAUDE.md covers the "why".

**[GLOSSARY.md](GLOSSARY.md)** -- What does this term mean here? Short
definitions for the three layers, the three agents, the gate, `R_best`,
HEAD, snapshots, the journal, splits and budgets, noting where the repo's
meaning differs from common usage.

**[RESULTS.md](RESULTS.md)** -- What did it actually score? The
deterministic mock-backend run, one live run against real models with a
per-family breakdown, the parallelism speedup, cost per inference call, and
the caveats to read before quoting any number.

**[EXTENDING.md](EXTENDING.md)** -- How do I point this at my own tasks?
What a benchmark must supply (tasks, an environment, a scorer), where to
wire it in, which task shapes the method can help with, and why the bundled
benchmark does not yet test the compounding claim.

**[CONTEXT-ENGINEERING.md](CONTEXT-ENGINEERING.md)** -- Why is the repo
shaped like this? Working notes on the paper's "more context scored worse"
ablation and the append-only-source / derived-artifact arrangement that also
shows up in Zettelkasten, Second Brain, LLM Wiki and BMAD. It separates what
is measured from what is only argued.

**[COMMIT-HISTORY.md](COMMIT-HISTORY.md)** -- How did the repo get here?
Every commit, oldest first, with its full message. Useful when you have a
zip without `.git`; if you have `.git`, `git log` is authoritative.

## COMMIT-HISTORY.md is generated

It is written by
[../scripts/gen_commit_history.py](../scripts/gen_commit_history.py).
Do not hand-edit it: the next run overwrites the whole file. To update it:

```bash
python scripts/gen_commit_history.py
```

It is generated before the commit that records it, so it always lags the
latest commit by one. See [../scripts/README.md](../scripts/README.md).

## Keeping these honest

Every relative link in every `.md` file is checked by
`tests.test_tutorials.TestDocLinks`, with fenced blocks and inline code
stripped first. If you add a document here, add a line to the index above
and run:

```bash
python -m unittest tests.test_tutorials.TestDocLinks -v
```

If a document makes claims about a command or flag, check each one against
the code. Reading the prose is not enough; see the "Generated content needs
verifying" scar in CLAUDE.md.
