# wikiskill

The Python package that implements the WikiSkill loop. This file maps the
code: what each module is for, how a `run` moves through it, and where each
invariant in [CLAUDE.md](../../CLAUDE.md) is enforced. For the method itself
read the [repo README](../../README.md); for the layer diagram and the
on-disk layout read [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md).

## Modules

| Module | What it is for |
|---|---|
| `cli.py` | `argparse` front end. `build_parser` defines the flags and subcommands; `config_from` turns them into a `RunConfig`; `main` dispatches. |
| `loop.py` | `Journal`, `Workspace`, `Evaluator` and `EvolutionLoop`: the seven-phase orchestrator and the resume logic. |
| `config.py` | `RunConfig`, the workspace `Paths`, the default model ids, and `MODEL_CAPS` / `caps_for`. |
| `gating.py` | `decide` (the accept/reject rule) and `check_budget` (the byte ceilings). |
| `patching.py` | `apply_batch`: validates and applies wiki `PatchOp`s over an in-memory dict. |
| `protocol.py` | Parsers for the `THOUGHT:` / `ACTION:` / `ANSWER:` text protocol and fenced JSON. |
| `types.py` | The dataclasses that cross a disk or model boundary: `Task`, `Trace`, `Skill`, `SkillSet`, `PatchOp`, `Proposal`, `IterationResult`. |
| `util.py` | Atomic UTF-8/LF writes, `content_sha`, `canonical_json`, `safe_join`. Use these rather than `open()`. |

| Subpackage | What it is for |
|---|---|
| [agents/](agents/README.md) | The three model-driven roles: inference, wiki maintainer, skill proposer. |
| [layers/](layers/README.md) | The on-disk stores for `raw/`, `wiki/` and `skills/`. |
| [backends/](backends/README.md) | `complete(LLMRequest) -> LLMResponse` over mock, `claude -p`, or the SDK. |
| [bench/](bench/README.md) | The bundled records-service benchmark: tasks, environment, scorer. |

## How a `run` flows

1. `cli.main` builds a `RunConfig` and an `EvolutionLoop`.
2. `EvolutionLoop.__init__` opens the `Workspace` (which builds `RawStore`,
   `WikiStore`, `SkillSetStore` and `Journal`), gets a backend from
   `backends.get_backend` wrapped in `CachingBackend`, loads
   `starter.tasks()`, and constructs the three agents.
3. `EvolutionLoop.run` scores a no-skills baseline on `val` once, returns at
   once if `R_best` already meets `early_stop_score`, and otherwise starts at
   `Journal.last_committed() + 1`.
4. `EvolutionLoop.iterate` runs the phases. `Evaluator.run` drives
   `InferenceAgent.run` over the train split in a thread pool.
   `WikiMaintainer.run` patches the wiki. `SkillProposer.run` returns one
   `Proposal`. The loop checks that cited patterns exist and that an `edit`
   targets a real skill, then calls `check_budget`, `SkillSetStore.materialize`,
   evaluates candidate and incumbent on `val`, and calls `gating.decide`.
5. Accept: `set_head(candidate_sha, ...)`, journal `commit`, then
   `append_skill_impact`. Reject: `_reject` keeps HEAD on the parent sha and
   still writes the impact record.

The phase list and the "decide, journal, then act" rule are explained in
[docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md#the-seven-phases).

## Where each invariant lives

| CLAUDE.md invariant | Enforced in |
|---|---|
| 1. Inference never reaches the wiki | `InferenceAgent.__init__(backend, model, max_steps)` in `agents/inference.py`, which does not import `layers.wiki`. `SkillSet.render_for_prompt` in `types.py` is the only channel into its prompt. Checked by [tests/test_no_wiki_leak.py](../../tests/test_no_wiki_leak.py). |
| 2. The wiki has no delete path | `WikiStore` in `layers/wiki.py` has no delete method. Its writers are `apply_patch_ops`, `append_log`, `append_skill_impact`. |
| 3. Wiki patches are all-or-nothing | `patching.apply_batch` returns the original pages on the first error; `WikiStore.apply_patch_ops` writes only when `outcome.ok`. |
| 4. Anchors match exactly once | `_apply_one` in `patching.py` raises `E_ANCHOR_AMBIGUOUS` when the anchor count is above one. |
| 5. HEAD moves last | `EvolutionLoop.iterate` journals `gate_decision` before `SkillSetStore.set_head`. `Journal.last_committed` drives resume. |
| 6. `skill-impact.md` is harness-written | Only `EvolutionLoop.iterate` and `_reject` call `WikiStore.append_skill_impact`. No agent does. |
| 7. Traces bucketed by skill-set sha | `trace_id` and `RawStore.bucket` in `layers/raw.py` both include `skillset_sha[:8]`. |

## Things that are not what they look like

- `RunConfig.bench` exists but nothing reads it. `loop.py` and
  `agents/inference.py` import `bench.starter` directly. Swapping the
  benchmark is described in [docs/EXTENDING.md](../../docs/EXTENDING.md).
- `LLMRequest.context` carries hints for the mock backend only.
  `EvolutionLoop._mock_context` builds the proposer's. No real backend sends
  it to a model.
- `EvolutionLoop.evaluate` (the `eval` and `report` commands) uses iteration
  `99` and never touches HEAD, the wiki or the journal, so scoring a
  hand-written `--skills-dir` cannot corrupt a run.

## Running it

```bash
python -m unittest discover -s tests -t .
python -m wikiskill.cli --workspace ws --backend mock --decoy-iteration 3 run -k 8
```

`--decoy-iteration` only affects the mock backend: it makes the mock
proposer emit a useless skill at that iteration so the rejection path runs.
