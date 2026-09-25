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

**The Windows `.CMD` shim silently corrupted every system prompt.**
`shutil.which("claude")` returns `claude.CMD`, a batch wrapper. Batch mangles
arguments containing `{`, `%`, quotes and newlines -- which is every prompt
this package sends. It does not error. The model simply receives garbled
instructions and answers in prose, so the bug presents as a *prompting*
problem and you can burn an hour rewriting prompts that were never delivered.
`resolve_executable()` now skips the shim and runs
`node_modules/@anthropic-ai/claude-code/bin/claude.exe` directly.

**`--append-system-prompt` left Claude Code's identity in charge.** Appending
puts our instructions *after* the default coding-agent prompt, and the
default wins: asked to look up a record, the model went hunting for a real
records service in the repo and explained it could not find one. Use
`--system-prompt` to replace. Side benefit that is not a side benefit: it
drops ~25k tokens of default prompt per call, taking cost from $0.052 to
$0.0016 -- a 33x difference that decides whether a full run is affordable.

**`--allowed-tools ""` does not disable tools; `--tools ""` does.** They are
different options and the first one quietly does nothing. An evaluated model
with real Read and Bash can solve -- or appear to solve -- a simulated task
by means the trace never records, which makes every downstream wiki pattern
fiction. `--restricted` and `--strict-mcp-config` close the same hole for
settings files and MCP servers.

**`claude auth status` reports `loggedIn: true` for expired credentials.**
It does not check `expiresAt`. A CLI with a 105-day-expired access token and
an empty refresh token reported healthy while failing every start with a
message blaming *managed settings*. When the CLI will not start, read
`expiresAt` out of `~/.claude/.credentials.json` before believing any status
command, and re-auth with `claude auth login`.

**A validation task passed without its skill.** Two of the original
`round_even` amounts rounded identically under half-even and half-up, so the
split carried no signal for that family and the baseline looked better than
it was. Every benchmark value must actually discriminate; assert it.

**`os.replace` fails intermittently on Windows.** Atomic writes started
failing with "Access is denied" on `HEAD.json`, on one machine, at random.
Nothing in the code was wrong: an antivirus scanner or the search indexer
holds a handle on the destination for a few milliseconds after we write it.
`util._replace_with_retry` retries with backoff. Each attempt is still a
single rename, so atomicity is unchanged. A nondeterministic failure that
only reproduces on some machines is worth a fix even when the code is
correct.

**One broken exercise took down discovery of all the others.** A zero-byte
`check.py` from an interrupted write made `tutorials/check.py` raise during
discovery, so three unrelated tests errored and the real cause was four
stack frames away. Discovery now reports a broken exercise *as* a failing
exercise. When you are enumerating plugins, exercises, or skills, one bad
entry must never hide the good ones.

**A checker that cries wolf gets ignored.** The docs link checker flagged an
*illustrative* link inside a code example -- the LLM Wiki track demonstrates
a dual-link format whose sample path deliberately points nowhere. It now
strips fenced blocks and inline code before looking for links. A false
positive in a lint is worse than no lint, because it teaches people to skip
the output.

**`open(path, "w")` on Windows writes CRLF and uses the locale codepage.**
The persona exporter did both. The repo pins LF via `.gitattributes` and
`export.py --check` compares bytes, so the exports would have matched
locally and failed `--check` on any fresh clone -- and the locale encoding
would have mangled the Pi character in the rubric persona. Always pass
`encoding="utf-8"` and, for writes, `newline` explicitly.

**Generated content needs verifying, not trusting.** Tutorial prose written
by a subagent self-reported success and contained three invented LLM Wiki
flags (`audit --report`, `compile --project`, `archive unarchive`). They
were found by scanning every command and flag in the tutorials against the
installed command definitions, not by reading. If you generate docs about a
tool, diff the claims against the tool.

**An unquoted YAML rule turned OpenSpec's rules off.** Track 50's
`openspec-config.yaml` first listed a rule as
`- End every requirement with "Trace: PRD-<n>"`. The `: ` inside it makes
YAML read a mapping, and OpenSpec's response was one warning line and
*every* rule for that artifact ignored -- so `/opsx:propose` would have
written specs with no trace lines, and the judge would have blamed the
learner. Rules containing `: ` are single-quoted, and a test asserts it.
Check what the AI will actually see with
`openspec instructions <artifact> --change <id>`.

## Style

- LF endings, UTF-8, atomic writes. `util.py` has the helpers; use them.
- Never write `workspace/` from anywhere but `layers/`.
- Comments explain *why*, especially where the non-obvious choice is load-bearing. Do not add comments restating what the line does.
