---
name: "specgate: check"
description: "Run the specgate gate layers on a change"
allowed-tools: Bash(specgate:*)
category: "Validation"
tags: ["validation", "testing", "gates"]
---

Run the specgate gates on a change directory.

Run:
```bash
specgate check --change openspec/changes/<feature> --layers L0-L5
```

**Options** (the full CLI; `check` is its only subcommand):
- `--change DIR`: change directory holding `prd.md` (default: cwd)
- `--layers Lx-Ly`: layers to run, e.g. `L2` or `L0-L5`
- `--staged`: skip the gate when nothing is staged
- `--output PATH`: where to write `trace.json` (default: `trace.json`)

**Exit codes:** `0` all requested layers passed; `10+L` layer L failed (exit 12 = L2); `2` bad arguments.

**Layers:**
- **L0**: schema validation
- **L1**: static analysis
- **L2**: trace (markers and asserts)
- **L3**: execution tests
- **L4**: coverage
- **L5**: mutation testing
- **L6**: debate. The CLI does not run L6 (it returns no findings); see `/specgate:debate`.

On success the CLI writes `trace.json` to `--output`.
