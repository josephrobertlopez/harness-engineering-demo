# Lesson 1 — Setup: `bmad setup` and the `_bmad/` folder

## What `bmad setup` does

`bmad setup` is an idempotent upsert. Running it on a repo that already has
`_bmad/` updates it in place. The command creates:

- `_bmad/config.toml` — your project's BMAD settings
- `_bmad/scripts/` — shell scripts for the skills to call
- `_bmad/custom/` — where you write custom skills that stay in git

All skills themselves live globally in `~/.claude/skills/` (installed once,
used everywhere), so a repo with no `_bmad/` can still reach any global skill
— this is the first thing an unprepared user hits.

## Hard requirement: `uv`

BMAD requires `uv`. Check your version:

```bash
uv --version
```

Confirm it is 0.12.5 or higher. `uv` is the Python package installer that
replaces pip. If you don't have it, install it from https://docs.astral.sh/uv/.

## Run setup

```bash
bmad setup
```

On success, you will see:

```
BMAD initialized: _bmad/
  Scripts: _bmad/scripts/
  Config:  _bmad/config.toml
  Custom:  _bmad/custom/
```

If the command does not exist, add `~/.claude` to your PATH or run it as:

```bash
python -m bmad.cli setup
```

On Windows PowerShell, use:

```powershell
bmad setup
```

(If you see `bmad setup is deprecated`, your `~/.claude` installation is
old. Update it with `claude upgrade`.)

## Verify the structure

After setup, verify that `_bmad/` exists and contains the three folders:

```bash
ls -la _bmad/
```

Expected output:

```
_bmad/
├── config.toml
├── custom/
└── scripts/
```

`config.toml` is where you will (later, in later lessons) configure which
model to use, token budgets, and other project-specific settings.

## What happens on your first `bmad` command

The first time you run `bmad-spec` or any other skill, it checks for `_bmad/`
in your repo. If it does not find one, it halts with:

```
BMAD is not set up here. Run: bmad setup
```

This is not a bug, it is a feature: `bmad setup` is the boundary between
using the skills in any project (which works fine — they are global) and
committing to the full spec-driven workflow (which requires `_bmad/` in git).

---

Next: [Lesson 2 — Hello world](lesson-02-hello-world.md)
