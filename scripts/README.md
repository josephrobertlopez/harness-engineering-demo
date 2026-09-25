# scripts

Two maintenance scripts. Neither is part of the method, neither is needed to
run the loop or the tests, and both are stdlib only. Run them from anywhere:
each finds the repo root from its own location.

## `gen_commit_history.py`

Regenerates [../docs/COMMIT-HISTORY.md](../docs/COMMIT-HISTORY.md) from
`git log`, oldest commit first, with each commit's full message body.

```bash
python scripts/gen_commit_history.py
```

It takes no arguments. It prints `wrote docs/COMMIT-HISTORY.md (N commits)`
and exits non-zero with git's error if `git log` fails, so it needs a checkout
with `.git`.

Why it exists: the repo has no remote, and a zip copied without `.git`
loses the reasoning behind every decision. A plain-text record survives that.

When to run it: before committing, when you want the record current. The
file is generated before the commit that records it, so it always lags the
latest commit by one. That is expected. Never hand-edit the output; your
edits are overwritten on the next run.

## `make_zip.py`

Packages the repo as a handoff zip.

```bash
python scripts/make_zip.py
python scripts/make_zip.py --no-git
python scripts/make_zip.py --out path/to/handoff.zip
```

| flag | effect |
|---|---|
| (none) | writes `<repo-name>-<YYYY-MM-DD>.zip` in the repo's *parent* directory, `.git` included |
| `--no-git` | leaves out `.git`; the default filename gets a `-source` suffix |
| `--out PATH` | writes to `PATH` instead |

Why the parent directory: an archive written inside the repo would end up
inside the next archive. `.zip` files are excluded anyway.

Why `.git` is included by default: CLAUDE.md says what the invariants are,
but only the commits say what broke and why. Pass `--no-git` only if you
really do not want the history.

Always left out: `__pycache__`, `.venv`, tool caches, `node_modules`,
`.pyc`/`.pyo`/`.zip` files, and run artifacts under `workspace/.state/`,
`workspace/raw/iter-*` and `workspace/raw/eval-*`. Any run regenerates those.

It writes an entry for every directory, including empty ones. `git gc` can
leave `.git/refs/` empty, and a zip without that directory extracts to
something git reports as "not a git repository".

After writing, it prints the longest path inside the archive and how long
the extraction directory can be before Windows hits its 260-character
`MAX_PATH` limit, with a warning when there is little headroom. Extract
somewhere short, like `C:/dev`, if it warns.

When to run it: when handing the repo to someone who will not clone it.
