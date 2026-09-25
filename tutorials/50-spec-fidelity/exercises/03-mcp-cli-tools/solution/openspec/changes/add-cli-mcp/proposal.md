## Why

Engineers want Claude Code to inspect repositories with git and ripgrep. The
previous attempt exposed an arbitrary shell, which gave the model an
unbounded surface. A fixed, read-only, four-tool MCP server gives the same
insight with a surface the guild can review line by line. Traces to
`prd.md` (DEVX-311).

## What Changes

- Add a stdio MCP server (`2025-06-18`) exposing `git_status`, `git_log`,
  `git_diff_stat` and `rg_search`.
- Confine every command to a `--root` directory; reject paths that escape it.
- Run commands as argument lists with a 10 s timeout and an 8000-character
  output cap; report failures as `isError` results.
- Ship `.mcp.json` and document `claude mcp add`.

## Capabilities

### New Capabilities

- `cli-mcp`: an MCP tool server over a fixed set of read-only git and
  rg commands.

### Modified Capabilities

None.

## Impact

New code only: `impl/server.py`, `impl/.mcp.json`. No dependencies beyond
the git and rg binaries.
