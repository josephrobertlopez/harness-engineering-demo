---
name: "specgate: init"
description: "Set up the specgate gates in a repo by hand"
allowed-tools: Bash(specgate:*)
category: "Workflow"
tags: ["setup", "initialization", "workflows"]
---

There is no `specgate init` subcommand. Set the gates up with these steps:

1. Install the CLI into the repo's `.venv` (lefthook expects `.venv/bin/specgate`):
   ```bash
   uv venv --python 3.12 && uv pip install -e "plugins/specgate[dev]"
   specgate check --help
   ```
2. Add a pre-commit gate to `lefthook.yml`:
   ```yaml
   pre-commit:
     commands:
       specgate:
         run: .venv/bin/specgate check --layers L0-L2 --staged
   ```
3. Copy `.github/workflows/spec-gate.yml` and `.github/workflows/kt-docs.yml` from this repo.
4. Create a change directory, `openspec/changes/<feature>/prd.md`, and run:
   ```bash
   specgate check --change openspec/changes/<feature> --layers L0-L5
   ```
