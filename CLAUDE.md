# Working in this repo

An implementation of WikiSkill (arXiv 2608.27454). Read `README.md` first for
what the method is; this file is about not breaking it.

## Run things

```bash
python -m unittest discover -s tests -t .
```

Stdlib only, Python 3.12+. No install step, no network, no API key. If a
change makes that untrue, it is the wrong change.

```bash
python -m wikiskill.cli --workspace ws --backend mock --decoy-iteration 3 run -k 8
```

## Invariants — do not "clean these up"

**1. The Inference Agent must never reach the wiki.**
`InferenceAgent.__init__` takes `(backend, model, max_steps)` and nothing
else; `agents/inference.py` does not import `layers.wiki`. This is the
paper's load-bearing ablation (63.7% → 60.9% when inference can read the
wiki). It is enforced by signature, not by a prompt line, precisely so a
refactor cannot quietly undo it. `tests/test_no_wiki_leak.py` will fail if you
add the parameter "for convenience".

**2. The wiki has no delete path.**
`WikiStore` exposes `apply_patch_ops`, `append_log`, `append_skill_impact`.
That is the whole write surface. The wiki is never rolled back, so rollback
must be structurally unable to reach it. Unbounded growth is a *known and
accepted* limitation of the method — do not add pruning without saying so
loudly in the README.

**3. Wiki patches are all-or-nothing.**
Because the wiki is never rolled back, a half-applied batch is permanent
damage. `patching.apply_batch` works on an in-memory dict and only a fully
successful batch is written. Never write pages mid-batch.

**4. Anchors must match exactly once.**
`E_ANCHOR_AMBIGUOUS` is not pedantry. "First occurrence" semantics corrupt
pages silently as they grow, on a layer with no undo.

**5. HEAD moves last.**
Decide, journal, then act. The gate decision is durable before `set_head`
runs, so a crash between them replays to the same place. Rollback is "never
move HEAD" — there is no undo path, and adding one would create a bug class
that currently cannot exist.

**6. `skill-impact.md` is written by the harness, never by a model.**
A model is not asked to self-report whether its own proposal was accepted.

**7. Trace paths are bucketed by skill-set sha.**
Within one iteration the same validation task runs under both incumbent and
candidate. Dropping the sha from the path makes them overwrite each other and
the gate compares a score against itself.

## Model API facts that bite

Model ids are complete as written — **never append a date suffix**.

| model | thinking | effort | sampling |
|---|---|---|---|
| `claude-opus-5`, `claude-sonnet-5` | `{"type": "adaptive"}` | `output_config.effort` | **400 on `temperature`** |
| `claude-haiku-4-5` | `{"type": "enabled", "budget_tokens": N}` | **errors** | allowed |

`budget_tokens` must be ≥1024 and < `max_tokens`. All of this lives in
`config.MODEL_CAPS` and is applied in `backends/anthropic_api.py` — one table,
not scattered conditionals. `tests/test_backend_params.py` guards it.

An unset `ANTHROPIC_API_KEY` does **not** mean there are no credentials: the
SDK also resolves `ANTHROPIC_AUTH_TOKEN` and `ant auth login` profiles.

## Scar tissue

Things that were wrong here once, and the reason each fix looks the way it does.

**The maintainer's sample cap starved a whole family.** The first version took
two traces per family and truncated to a budget of eight. With five families
that dropped the last one alphabetically — so `round_even` was never sampled,
never documented, no skill was ever proposed for it, and the run plateaued at
0.80 with nothing in the logs explaining why. Sampling is now two passes:
one trace from *every* family first, second traces only with leftover budget.
Breadth before depth, whenever a budget meets a stratified sample.

**`os.replace` cannot rename a directory on Windows.** It maps to
`MoveFileEx(MOVEFILE_REPLACE_EXISTING)`, which refuses directories and fails
with "Access is denied" even when the destination does not exist. Snapshot
materialization uses a plain `rename` onto a non-existent path. This is also
why HEAD is a pointer *file* and not a swapped directory.

**Resume skipped the iteration it crashed in.** Restart used
`last_journal_entry + 1`. A crash partway through iteration 3 leaves 3's
earlier phases journaled, so the resumed run began at 4 and produced a
silently shorter history than an uninterrupted one. Restart is now keyed off
the last iteration that reached `commit`.

**A converged run was not idempotent.** `run` re-entered past the early-stop
point and burned more iterations — free on the mock, real money otherwise.
It now returns immediately when `R_best` has already hit `early_stop_score`.

**A validation task passed without its skill.** Two of the original
`round_even` amounts rounded identically under half-even and half-up, so the
split carried no signal for that family and the baseline looked better than
it was. Every benchmark value must actually discriminate; assert it.

## Style

- LF endings, UTF-8, atomic writes. `util.py` has the helpers; use them.
- Never write `workspace/` from anywhere but `layers/`.
- Comments explain *why*, especially where the non-obvious choice is load-bearing. Do not add comments restating what the line does.
