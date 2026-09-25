# tests

The suite that keeps the invariants in [../CLAUDE.md](../CLAUDE.md) true.
Stdlib `unittest` only. No install step, no network, no API key.

## Run it

From the repo root:

```bash
python -m unittest discover -s tests -t .
```

`-t .` makes the repo root the top level, so `tests` imports as a package
and `from tests import context` resolves. Use a Python 3.12+ interpreter; if
`python` on your machine is older, call `python3.12` instead.

One module, one class, or one test:

```bash
python -m unittest tests.test_no_wiki_leak -v
python -m unittest tests.test_tutorials.TestDocLinks -v
python -m unittest tests.test_patching.TestApply.test_batch_is_all_or_nothing
```

## What each module guards

| module | guards |
|---|---|
| `test_backend_params.py` | Per-model request shape from `config.MODEL_CAPS`: no date suffixes, adaptive thinking and no sampling params on Opus 5 / Sonnet 5, `budget_tokens` and no effort on Haiku 4.5, refusals raised. |
| `test_claude_cli_backend.py` | The CLI backend fails loudly instead of passing an error off as a reply; isolation flags; the Windows `.CMD` shim is bypassed. |
| `test_concurrency.py` | Parallel rollouts give the same traces, order and workspace as sequential ones; cached rollouts are not re-run; cost totals survive threads. |
| `test_e2e_mock.py` | A full offline run on the mock backend actually learns: converges, rejects the decoy, beats the no-skills baseline on the test split. Sockets are denied for the whole class. |
| `test_gating.py` | The gate's strict-improvement rule, margin, byte budgets, and that the budget CLI flags reach `RunConfig`. |
| `test_invariants.py` | Invariants 2 and 7, which the code alone held: the wiki's public surface is exactly the declared one with nothing that can undo, and the same task under two skill sets gets two trace paths. Also checks any test count stated in README.md or START-HERE.md. |
| `test_no_wiki_leak.py` | The Inference Agent cannot reach the wiki; the Proposer can. |
| `test_patching.py` | Wiki patch path validation, evidence rules, anchor rules, all-or-nothing batches. |
| `test_personas.py` | `personas/export/` matches a fresh `personas/export.py` run, every persona has every surface, and every persona file is LF. |
| `test_protocol.py` | Parsing of the `THOUGHT:` / `ACTION:` / `ANSWER:` protocol and fenced JSON blocks. |
| `test_resume.py` | A crash mid-iteration resumes to the same workspace as a clean run; reruns duplicate nothing; a converged run is a no-op. |
| `test_skills_store.py` | Skill-set sha, snapshot materialisation, rejection leaving HEAD alone, mirror repair, LF diffs. |
| `test_spec_fidelity.py` | Track 50's judge: the quotes lesson 4 makes, gaming attempts, false positives, and that every rubric value discriminates. |
| `test_tutorials.py` | Every exercise passes with its `solution/` and fails with a hint when empty; every relative Markdown link resolves. |

## Which tests hold which invariant

| CLAUDE.md invariant | enforced by |
|---|---|
| 1. Inference never reaches the wiki | all of `test_no_wiki_leak.py` (signature is exactly `self, backend, model, max_steps`; no `layers.wiki` import) |
| 2. No wiki delete path | `test_invariants.TestWikiHasNoDeletePath` |
| 3. Patches are all-or-nothing | `test_patching.TestApply.test_batch_is_all_or_nothing` |
| 4. Anchors match exactly once | `test_patching.TestApply.test_anchor_must_be_unique` |
| 5. HEAD moves last | `test_skills_store.TestStore.test_rejecting_leaves_head_untouched`, `test_resume.py`, `test_e2e_mock.TestEndToEnd.test_head_moved_exactly_once_per_acceptance` |
| 6. `skill-impact.md` written by the harness | `test_e2e_mock.TestEndToEnd.test_skill_impact_has_one_record_per_proposal` checks one record per proposal; it does not prove who wrote it |
| 7. Trace paths bucketed by sha | `test_invariants.TestTracePathsCarryTheSha` |

The model API table is guarded by `test_backend_params.py`. Several scars
have their own test too: the `--system-prompt` / `--tools ""` flags
(`test_isolation_flags`), resume and idempotent reruns (`test_resume.py`),
the link checker ignoring code (`TestDocLinks`), quoted OpenSpec rules
(`test_openspec_rules_are_quoted`) and CRLF exports (`test_everything_is_lf`).

## Writing a new test

- Name the file `test_*.py` so discovery finds it. Use `unittest.TestCase`.
  No pytest, no third-party packages.
- Put `from tests import context  # noqa: F401` before any `wikiskill`
  import. `tests/context.py` adds `src/` to `sys.path`; that is the whole
  reason there is no install step.
- Stay offline. Use `backend="mock"`, or `mock.patch("subprocess.run", ...)`
  for the CLI backend. A test that needs a key or a network is the wrong
  test for this suite.
- Work in `tempfile.TemporaryDirectory()`. Never write the repo's
  `workspace/`; only `layers/` writes there.
- Pass `encoding="utf-8"` on every read and write, and `newline="\n"` on
  every write. On Windows `open(path, "w")` writes CRLF in the locale
  codepage, and the repo compares LF bytes.
- Make every fixture value discriminate. A case that passes with and
  without the behaviour under test checks nothing (see the `round_even`
  scar in CLAUDE.md).
- Give the module or test a docstring that says *why* the property matters,
  like the existing ones. The docstring is what the next person reads when
  it fails.
