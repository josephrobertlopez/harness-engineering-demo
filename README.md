# harness-engineering-demo

**A small harness for a context-engineering question: does the thing you
just put in the model's context actually pay for itself?**

It implements **WikiSkill** ([arXiv 2608.27454](https://arxiv.org/html/2608.27454),
*Compiling Agent Experience into Persistent Knowledge for Skill Evolution*)
— an agent that writes its own instructions and keeps only the ones that
measurably help — and six tutorial tracks around it.

## The context-engineering bit

A skill is just curated context. The interesting question is not "what
should I write" but "how would I know it helped", and that needs a harness:
something that runs the agent, records what it did, and scores a change
against a split it was not tuned on.

The paper's sharpest result is a context-engineering result, and it is
counter-intuitive. Giving the agent **more** context made it **worse**:

| what the agent can read | average score |
|---|---|
| distilled skills only | **63.7%** |
| skills **plus** the accumulated notes | 60.9% |
| no skills at all | 48.7% |

The notes are what produced the skills. Handing them over too lowers the
score — so the value is in the distillation, not the material. This repo
enforces that structurally: the inference agent has no wiki handle, and a
test fails if anyone adds one.

## A pattern I noticed while building it

Not a claim, an observation, and I found the prior art afterwards rather
than setting out to apply it. Three systems here keep the thing you *edit*
separate from the thing you *read*:

| | append-only source | derived artifact |
|---|---|---|
| [**LLM Wiki**](#credits) | `raw/` — re-ingest, never overwrite | articles and indexes |
| [**BMAD**](#credits) | `.memlog.md` | `SPEC.md`, re-derived each run |
| **This harness** | traces, wiki patterns | `skills/` |

It buys concrete things — LLM Wiki can run parallel research and still
compile one article; BMAD can take a PRD and a UX doc in any order because
nothing is merged. Niklas Luhmann was doing it with index cards in the
1950s. [docs/CONTEXT-ENGINEERING.md](docs/CONTEXT-ENGINEERING.md) has the
longer version, and is explicit about which parts are measured and which
are just me noticing a resemblance.

Measured here, with real models: a held-out test split went from **0.400 to
1.000** after one iteration of the loop. The full numbers and the caveats
that matter are in [docs/RESULTS.md](docs/RESULTS.md).

```
python -m unittest discover -s tests -t .     # 119 tests, ~1 min
```

No install, no API key, no network. Python 3.12+ and nothing else.

> The repo is named for what it demonstrates — how to engineer an agent
> harness. The Python package and CLI keep the method's own name,
> `wikiskill`, so the code lines up with the paper it implements.

The paper's claim is that agents improve not by accumulating transcripts but by
**compiling** them. Experience is separated into three layers — immutable raw
traces, a compounding wiki of patterns, and executable skills — and skills
evolve under a validation gate that rolls back anything that does not help.
Reported result: evolved skills let a smaller model beat a larger one running
without them (Qwen-3.5-9B + WikiSkill at 47.4% vs Qwen-3.6-27B at 39.4%).

This repo runs that loop end to end, offline, on a bundled benchmark.

```bash
python -m wikiskill.cli --workspace ws --backend mock --decoy-iteration 3 run -k 8
```
```
iter 1: train=0.00 val cand=0.20 inc=0.00 -> ACCEPT  R_best=0.20
iter 2: train=0.20 val cand=0.40 inc=0.20 -> ACCEPT  R_best=0.40
iter 3: train=0.40 val cand=0.40 inc=0.40 -> REJECT (no_improvement)  R_best=0.40
iter 4: train=0.40 val cand=0.60 inc=0.40 -> ACCEPT  R_best=0.60
iter 5: train=0.60 val cand=0.80 inc=0.60 -> ACCEPT  R_best=0.80
iter 6: train=0.80 val cand=1.00 inc=0.80 -> ACCEPT  R_best=1.00
```

Held-out test goes 0.000 → 1.000. Iteration 3 is a real rejection with a real
rollback, not a decorative one.

## What this is not

- **Not a library.** It is a worked example you read and modify. There is no
  stable API and the seam you are meant to touch is documented in
  [docs/EXTENDING.md](docs/EXTENDING.md).
- **Not a benchmark result you should cite.** Five test tasks. See the
  caveats in [docs/RESULTS.md](docs/RESULTS.md) before quoting any number.
- **Not a reproduction of the paper's experiments.** It implements the
  method and runs it on a small task set of its own.

## Install

Nothing to install. The package is stdlib-only on Python 3.12+; the
`anthropic` SDK is an optional extra used by one backend.

```bash
git clone <this repo> && cd harness-engineering-demo
python -m unittest discover -s tests -t .
```

## The three layers

```
workspace/
  raw/                  immutable execution traces, one file per rollout
  wiki/
    patterns/<slug>.md  one failure mode or winning strategy per page
    logs.md             chronological, appended by the Wiki Maintainer
    skill-impact.md     per-proposal: diff, validation scores, verdict
    index.md            generated catalogue, the Proposer's entry point
  skills/<name>/        SKILL.md + PURPOSE.md — mirror of HEAD
  .state/               journal, content-addressed snapshots, LLM cache
```

`.state/` is not one of the paper's layers. It holds the phase journal and the
skill snapshots that make rollback and resume work.

## The loop

Seven phases per iteration, each idempotent:

```
rollout_train -> wiki_update -> propose -> apply_candidate
              -> eval_val -> gate_decision -> commit
```

1. **Inference Agent** runs the train split with the current skills. Traces land in `raw/`.
2. **Wiki Maintainer** samples traces across families, root-causes the failures, and applies *incremental* patches to `patterns/`.
3. **Skill Proposer** reads the pattern index and the impact ledger, pulls specific pages through `read_file`, and emits one atomic proposal for one skill.
4. **Gate** evaluates the candidate on held-out validation and accepts only a strict improvement. Otherwise HEAD does not move.

**The wiki is never rolled back.** A rejected proposal loses its skill; the
patterns that motivated it stay. That asymmetry is the mechanism — knowledge
compounds even when the skill built on it fails.

**The Inference Agent cannot see the wiki.** This is the paper's key ablation:
giving inference wiki access drops average performance from 63.7% to 60.9%;
removing the wiki entirely drops it to 48.7%. Here it is enforced structurally
— `InferenceAgent` takes no wiki handle and its module does not import the
wiki layer — and `tests/test_no_wiki_leak.py` asserts it.

## Backends

| Backend | Credentials | Determinism | Use for |
|---|---|---|---|
| `claude-cli` *(default)* | reuses the Claude Code login | none (cold) | real runs without an API key |
| `mock` | none | **fully deterministic** | CI, offline development |
| `anthropic` | `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or an `ant auth login` profile | on cache replay | real runs through the SDK |

`claude-cli` is the default because it needs no API key. Its cost: `claude -p`
is single-shot and takes no custom tool schemas, so the ReAct loops here use a
**parsed text protocol** (`THOUGHT:` / `ACTION:` / `ANSWER:`) rather than
native `tool_use` blocks. One protocol across all three backends, one set of
parsers to test.

Getting a clean measurement out of it needs four flags, all set automatically:
`--system-prompt` (replace, not append -- otherwise Claude Code's coding-agent
identity overrides the benchmark instructions, and you pay ~25k extra tokens
per call for the privilege), `--tools ""` (the real kill switch;
`--allowed-tools ""` is a different option and disables nothing),
`--restricted` and `--strict-mcp-config` (so no CLAUDE.md, hook or MCP server
leaks into the run). On Windows the backend also bypasses the `claude.CMD`
shim, which corrupts any argument containing braces, quotes or newlines.

Model defaults: inference `claude-haiku-4-5`, maintainer `claude-sonnet-5`,
proposer `claude-opus-5` at `effort=high`. The backend branches on model
family because the shapes differ — Opus 5 and Sonnet 5 take adaptive thinking
plus `output_config.effort` and **reject `temperature`** with a 400; Haiku 4.5
takes `budget_tokens` and rejects `effort`. `tests/test_backend_params.py`
guards both.

## Honest notes on determinism

Three tiers, and only one of them is a guarantee:

- **`mock`** — byte-identical across runs. This is the CI contract.
- **`anthropic` / `claude-cli` on replay** — every response is cached at
  `.state/llmcache/<sha>.json`, so resuming re-issues zero model calls for
  completed work.
- **cold, against a real model** — not reproducible, and cannot be made so.
  `temperature` is removed on Opus 5 and Sonnet 5. `--seed` controls only
  harness-side randomness (trace sampling, ordering).

## Deviations from the paper

Both are deliberate, and both are places where a literal reading would be worse:

**Paired re-measurement at the gate.** The paper compares the candidate
against a stored `R_best`. Here the incumbent is re-scored in the same batch
as the candidate. With a five-task validation split one task is a twenty-point
swing and sampling cannot be pinned, so comparing against a score measured two
iterations ago accepts drift as if it were learning — and because an accepted
skill becomes the parent of every later proposal, that noise compounds into
the lineage. `--gate-margin` adds a further conservative bias; ties are always
rejected.

**Text protocol instead of native tool use.** See *Backends* above.

## Known gaps, inherited from the paper

Not fixed here, because the paper did not evaluate a fix and inventing one
silently would make this a different method:

- **No wiki pruning.** The wiki only grows. `WikiStore` has no delete API at all.
- **No skill retrieval.** Every skill is injected into the prompt, so the set only grows. Byte budgets (`--skill-budget-bytes`, `--skillset-budget-bytes`) are what stands between you and a prompt made mostly of old advice.
- **Strict gating excludes neutral proposals** that might have enabled a later gain.
- **Short task horizons.** The bundled benchmark is a handful of tool calls per task.

## The bundled benchmark

Twenty tasks over a simulated records service, in five *quirk families* —
each hiding one rule that cannot be inferred from the prompt, only discovered
by failing:

| family | the rule |
|---|---|
| `iso_z` | timestamps need a `T` separator and a trailing `Z` |
| `rec_prefix` | `fetch` only accepts the canonical uppercase `REC-` id |
| `page_two` | `search` paginates at three hits; the answer is often on page 2 |
| `round_even` | money rounds half-to-even at 2dp, not half-up |
| `idem_key` | write payloads need `idempotency_key` = `"<record>:<op>"` |

Four instances each: two train, one val, one test, disjoint by construction.
Every value is chosen so the task fails without the rule — the `round_even`
amounts, for instance, all round differently under half-even and half-up.

> The mock backend decides whether the simulated agent "knows" a rule by
> looking for a `[[QUIRK:<family>]]` marker in the skill body. That marker is
> a **simulation device for the offline test**, so it can assert genuine
> improvement. Real models read the prose; nothing in the loop depends on it.

Swap in your own tasks by replacing `bench/starter.py`'s `tasks()`,
`StarterEnv` and `score()` — the seam is a `Task` list, an environment with
`tool_spec()` / `call()`, and a pure scorer returning `(float, failure_summary)`.

## Commands

```
wikiskill init                                  create the workspace
wikiskill baseline --split val                  score with no skills at all
wikiskill run -k 8                              the evolution loop
wikiskill iterate                               exactly one iteration
wikiskill eval --split test --skills none       held-out baseline
wikiskill eval --split test --skills accepted   held-out, evolved
wikiskill status                                HEAD, R_best, accept/reject history
wikiskill show wiki|skills|impact|log           print an artifact
wikiskill report                                baseline vs evolved
```

Resume is automatic: `run` restarts from the first iteration that never
reached its commit phase.

## Measured, against a real model

One live run on the bundled benchmark, Haiku 4.5 as the inference agent,
Sonnet 5 maintaining the wiki, Opus 5 proposing:

| split | no skills | evolved | |
|---|---|---|---|
| validation (gated on) | 0.400 | 1.000 | contaminated -- it *is* the gate |
| **held-out test** | **0.400** | **1.000** | never gated on, never shown to any agent |

Converged in a single iteration. What the agent got wrong unaided is the
interesting part: it *passed* the two quirks the environment reveals
(`rec_prefix` -- it read the error and retried with the canonical id;
`page_two` -- it saw `more_pages` and paginated) and failed exactly the three
**silent conventions** nothing tells it about. That is the failure shape this
method is for.

Caveats worth stating: five test tasks, so 0.400 is 2/5 and 1.000 is 5/5.
And converging in one iteration means this benchmark demonstrates that a
skill helps -- not yet that knowledge *compounds across iterations*, which is
the paper's actual claim. A harder task set is the next thing this repo needs.

## Credits

Three of the six tracks are built on tools I did not write. All are MIT
licensed and worth your time on their own terms:

| Project | Author | Source |
|---|---|---|
| **BMAD-METHOD** — spec-driven development for AI-assisted work | bmad-code-org | [github.com/bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) |
| **LLM Wiki** — LLM-compiled knowledge bases for any agent | nvk | [github.com/nvk/llm-wiki](https://github.com/nvk/llm-wiki) · [llm-wiki.net](https://llm-wiki.net/) |
| **OpenSpec** — spec-driven development for AI coding assistants | Fission-AI | [github.com/Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) |
| **ai-literacy-superpowers** — habitat and harness engineering for Claude Code | Habitat-Thinking | [github.com/Habitat-Thinking/ai-literacy-superpowers](https://github.com/Habitat-Thinking/ai-literacy-superpowers) |

**Tracks 10, 20 and 50 are my reading of those projects, not their
documentation.** They are opinionated, they occasionally disagree with how
the tools present themselves, and they will drift as the upstreams change.
Go to the source for anything authoritative.

The method implemented here is from arXiv 2608.27454. The implementation,
its two documented deviations, and every bug in it are mine.

## Licence

MIT.
