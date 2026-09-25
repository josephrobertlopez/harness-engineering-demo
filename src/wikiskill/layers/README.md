# layers/

The stores for the paper's three layers. Each class owns one directory under
the workspace. The on-disk layout is drawn in
[docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md#where-state-lives).

**Only `layers/` writes `workspace/`.** That is the rule in
[CLAUDE.md](../../../CLAUDE.md). The code keeps it for `raw/`, `wiki/`,
`skills/`, the snapshots and `HEAD.json`. Three writes into `.state/` sit
outside this package today: `Journal.record` and the saved `proposal.json`
in `loop.py`, and the response cache in `CachingBackend`
(`backends/base.py`). New workspace writes belong here.

## raw.py: immutable traces

`RawStore` writes two files per rollout under
`raw/iter-NN/<split>/<sha8>/`:

- `<task_id>.steps.jsonl`, appended by `record_step` as each step happens,
  so a crash leaves a readable prefix.
- `<task_id>.trace.json`, written atomically and last by `commit`. Its
  existence is the completion marker. `Evaluator.run` calls `load` and skips
  any task that already has one.

`begin` renames a leftover `.steps.jsonl` with no trace to
`.jsonl.crashed-N` and the rollout starts over. Nothing here mutates or
deletes a finished trace.

The path is bucketed by skill-set sha, and `trace_id` includes
`skillset_sha[:8]`. This is required, not cosmetic. Within one iteration the
same validation task runs under both incumbent and candidate. Without the
sha the two rollouts overwrite each other and the gate compares a score
against itself.

`exists` and `find` resolve a trace id. The maintainer uses `exists` to check
cited evidence; the proposer's `read_file` uses `find`.

## wiki.py: the layer that is never rolled back

**The wiki has no delete path.** `WikiStore` writes through exactly three
methods: `apply_patch_ops`, `append_log` and `append_skill_impact`. There is
no delete and no whole-page overwrite, so rollback cannot reach the wiki
because no API exists for it to call. A rejected proposal loses its skill;
the patterns that motivated it stay. The cost is that the wiki only grows.
That is a known limitation inherited from the paper. Do not add pruning
without saying so loudly in the repo README.

- `apply_patch_ops` hands the current `pages()` to `patching.apply_batch`
  and writes only if every op succeeded. A half-applied batch on a layer with
  no undo would be permanent damage. Anchors must match exactly once
  (`E_ANCHOR_AMBIGUOUS`), and a `create_page` must cite a trace. After a
  write, `_rebuild_index` regenerates `index.md`.
- `append_log` adds an entry to `logs.md`.
- `append_skill_impact` adds one record per proposal to `skill-impact.md`:
  target, validation scores, verdict, reject reason and the unified diff. It
  is called by `EvolutionLoop`, never by a model. A model is not asked to
  report whether its own proposal was accepted.

`index()` is the compact catalogue the maintainer and proposer see instead of
full pages. `read_relative` backs the proposer's `read_file` and goes through
`util.safe_join`, so a path cannot escape the wiki root.

## skills.py: snapshots behind one pointer

`SkillSetStore` never edits a skill in place.

- `materialize` writes a `SkillSet` to `.state/skillsets/<sha>/` and returns
  the sha. Same content, same sha, so re-running after a crash rewrites
  nothing. It stages to `.tmp-<sha>` and uses a plain `rename` onto the
  non-existent destination, because `os.replace` cannot rename a directory
  on Windows.
- `set_head` writes `.state/HEAD.json` (`sha`, `iter`, `r_best`) and then
  `rebuild_mirror`. Accepting moves HEAD to the candidate. Rejecting leaves
  the sha on the parent, and the candidate snapshot is simply never pointed
  at. There is no undo path to get wrong. HEAD is a small file, not a
  swapped directory, for the same Windows reason.
- `skills/` is a human-readable mirror of HEAD. `Workspace.open` calls
  `mirror_is_stale` and repairs a crash between the HEAD write and the
  mirror rebuild.
- `unified_diff` uses `difflib`, not `git diff`, so the output does not
  depend on `core.autocrlf` or a nested repository.

`load_skillset_from_dir` reads a hand-written folder of `<name>/SKILL.md`
(`PURPOSE.md` optional). It backs `wikiskill eval --skills-dir`.

## Writing files

Use the helpers in `util.py`: `atomic_write_text`, `append_text`,
`write_json`, `read_text_lf`. They write UTF-8 with LF endings. A CRLF would
change a snapshot sha.
