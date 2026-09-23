# harness-engineering-demo

A working implementation of **WikiSkill** ([arXiv 2608.27454](https://arxiv.org/html/2608.27454),
*Compiling Agent Experience into Persistent Knowledge for Skill Evolution*).

> The repo is named for what it demonstrates -- how to engineer an agent
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
- **No skill retrieval.** Every skill is injected into the prompt. Byte budgets (`--skill-budget-bytes`) are the only defence against dilution.
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

## Licence

MIT.
