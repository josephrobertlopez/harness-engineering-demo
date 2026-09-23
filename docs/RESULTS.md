# Measured results

Real data from actual runs. All numbers in this file are measured in this
repository; none are invented or rounded differently.

## Fully deterministic: offline with mock backend

```bash
python -m wikiskill.cli --workspace ws --backend mock --decoy-iteration 3 run -k 8
```

With `PYTHONPATH=src`:

```
iter 1: train=0.00 val cand=0.20 inc=0.00 -> ACCEPT  R_best=0.20
iter 2: train=0.20 val cand=0.40 inc=0.20 -> ACCEPT  R_best=0.40
iter 3: train=0.40 val cand=0.40 inc=0.40 -> REJECT (no_improvement)  R_best=0.40
iter 4: train=0.40 val cand=0.60 inc=0.40 -> ACCEPT  R_best=0.60
iter 5: train=0.60 val cand=0.80 inc=0.60 -> ACCEPT  R_best=0.80
iter 6: train=0.80 val cand=1.00 inc=0.80 -> ACCEPT  R_best=1.00
```

Iteration 3 is a real rejection: the candidate (0.40) does not beat the
incumbent (0.40), so the gate rejects it. The mock backend decides whether
the simulated agent "knows" a rule by matching `[[QUIRK:<family>]]` markers
in the skill body. That marker is a **simulation device for offline testing**
so the benchmark can assert genuine improvement. Real models read the prose.

## Live, against real models

One run on the bundled benchmark, using the default models:

| Agent | Model |
|---|---|
| Inference | `claude-haiku-4-5` |
| Wiki Maintainer | `claude-sonnet-5` |
| Skill Proposer | `claude-opus-5` |

Results:

| split | no skills | evolved | notes |
|---|---|---|---|
| **validation** | **0.400** | **1.000** | contaminated — it *is* the gate |
| **held-out test** | **0.400** | **1.000** | never shown to any agent |

**Converged in one iteration.** The test set went from 2/5 correct to 5/5.

### Per-family breakdown

The interesting detail: what did the agent get *wrong* unaided?

| family | baseline | result | why |
|---|---|---|---|
| `rec_prefix` | FAILED | PASSED | the environment returned an error naming the canonical uppercase format; the agent read it and retried |
| `page_two` | FAILED | PASSED | the search result carried `more_pages: true`; the agent saw it and paginated |
| `iso_z` | FAILED | FAILED | **0.50** — nothing told it the output format needed a trailing `Z` |
| `idem_key` | FAILED | FAILED | **0.67** — produced `REC-4842-reconcile` instead of `REC-4842:reconcile` (dash vs colon) |
| `round_even` | FAILED | FAILED | **0.50** — rounded half-up instead of half-to-even; rounded 7.67 instead of 7.66 |

The model handled every quirk the environment *revealed* and failed every
**silent convention** nothing announced. That is the failure shape this method
targets.

### How the maintainer and proposer iterated

The Wiki Maintainer's first attempt to patch the patterns used underscores in
slugs — a violation of the path validator. It received the error and corrected
itself on the retry, demonstrating the bounded repair turn.

The maintainer also documented an unprompted strategy for `rec_prefix`:
"retry with the canonical uppercase id, ideally pre-normalise to skip the
wasted round trip". This is extracting a successful strategy from the passing
tasks — exactly what the paper says happens.

The skill the proposer wrote generalised rather than memorised: every worked
example used a *train* record, never a val or test answer.

## Parallelism

The same validation workload with different concurrency settings:

| concurrency | wall time | identical score |
|---|---|---|
| `--concurrency 1` (sequential) | 3m 48s | yes |
| `--concurrency 6` | 1m 34s | yes |

Speedup: **2.4x** on a five-task validation split. Not 6x because with only
five tasks the longest one dominates wall time, and other processes on the
machine also matter. Parallelism is safe — rollouts are independent by
construction, and the response cache's writes are atomic.

## Cost per inference call

Using the `claude-cli` backend (default, reuses Claude Code login):

```
~$0.0016 per inference call
```

This is after the isolation flags are set correctly. Without `--system-prompt`
to replace (not append) the system prompt, the cost is ~$0.052 — a 33x
difference that decides whether a full run is affordable. See `CLAUDE.md` for
the flag details.

## **Important caveats**

State these plainly, do not bury them:

1. **Five test tasks.** The test set has one task per family, so 0.400 is
   2/5 correct and 1.000 is 5/5 correct. The absolute numbers are inflated
   by the small scale.

2. **Convergence in one iteration.** The benchmark demonstrates *that a skill
   helps* — the agent does better with the evolved skill than without it.
   It does **not yet demonstrate** the paper's actual claim, which is that
   knowledge *compounds across iterations*. The skills learned in iteration 2
   should enable better skills in iteration 3; one iteration cannot show that.

3. **Simple task horizon.** The bundled benchmark tasks are a handful of tool
   calls each. Longer tasks with richer failure modes would reveal more of
   what the method can do.

A benchmark where the quirks *interact* — where skill 2 only pays off once
skill 1 exists — is the most valuable contribution anyone could make to this
repo. It would exercise the compounding knowledge claim.

---

See `docs/EXTENDING.md` for the seam to swap in your own benchmark and
measure what matters to you.
