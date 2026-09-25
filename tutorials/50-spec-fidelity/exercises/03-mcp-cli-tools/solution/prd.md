# PRD — MCP server for git and rg (DEVX-311)

Source ticket: `ticket.md` (DEVX-311). Each requirement cites the stakeholder
answer it came from.

## Problem

Engineers want Claude Code to inspect repositories with the same CLIs they
use. The last attempt exposed a "run any shell command" MCP tool, which
handed the model an unbounded surface. The guild wants a small, fixed,
read-only set of commands that Claude Code can discover and call, with
failures the model can read and recover from.

## Users

- **Engineers** using Claude Code in a repository.
- **The model**, which reads the tool list and the tool results.
- **The DevX guild**, which reviews what the server can run.

## Requirements

### PRD-1: MCP over stdio

The server SHALL speak MCP over stdio as newline-delimited JSON-RPC 2.0,
protocol version `2025-06-18`, answering `initialize`, `ping`, `tools/list`
and `tools/call`, and MUST NOT answer notifications.

- WHEN a client sends `initialize` THEN the result carries protocol version
  `2025-06-18` and a `tools` capability.
- WHEN the server is started as a process and sent two request lines THEN it
  writes two response lines.

Source: stakeholder-answers.md Q5.

### PRD-2: A fixed catalogue of four tools

`tools/list` SHALL return exactly `git_status`, `git_log`, `git_diff_stat`
and `rg_search`, each with a JSON Schema that rejects unlisted arguments.
The only binaries the server MUST ever run are git and rg.

- WHEN a client lists tools THEN it receives exactly those four names.

Source: stakeholder-answers.md Q1, Q2.

### PRD-3: git tools

`git_status` SHALL run `git status --porcelain=v1 --branch`; `git_diff_stat`
SHALL run `git diff --stat`; `git_log` SHALL run `git log --oneline -n <limit>`
with `limit` an integer from 1 to 50, default 10.

- WHEN `git_status` is called THEN the server runs exactly
  `git status --porcelain=v1 --branch` in the root.
- WHEN `git_log` is called with no arguments THEN it runs with `-n 10`.
- WHEN `git_log` is called with `limit` 51 THEN the result has `isError: true`.

Source: stakeholder-answers.md Q2.

### PRD-4: rg search

`rg_search` SHALL run
`rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`,
`pattern` required and non-empty, `path` defaulting to `.`. Exit status 1
(no matches) MUST be a successful result.

- WHEN `pattern` is `--files` THEN it is passed after `-e` and searched for
  literally, not parsed as a flag.
- WHEN rg finds nothing THEN the result is not an error and says so.

Source: stakeholder-answers.md Q2, Q4, Q5.

### PRD-5: Confined to the root

Every command SHALL run in the directory given by `--root`. A `path` that
resolves outside the root MUST be rejected with an `isError` result naming
the escape.

- WHEN `path` is `../..` THEN the result has `isError: true` and no command
  runs.

Source: stakeholder-answers.md Q3.

### PRD-6: Execution limits

Commands SHALL run as an argument list with no shell, a 10 second timeout,
and output cut at 8000 characters with a `[truncated]` marker. A missing
binary, a non-zero exit or a timeout MUST be an `isError` result.

- WHEN rg is not installed THEN the result has `isError: true` naming it.
- WHEN a command exceeds the timeout THEN the result has `isError: true`.
- WHEN output exceeds 8000 characters THEN it is cut and ends `[truncated]`.

Source: stakeholder-answers.md Q4, Q5.

### PRD-7: Protocol errors

An unknown tool name SHALL return JSON-RPC error -32602, an unknown method
-32601, and an unparseable line -32700.

- WHEN a client calls tool `rm_rf` THEN the response is error -32602.
- WHEN a client calls method `resources/list` THEN the response is error -32601.
- WHEN a client sends `{not json` THEN the response is error -32700.

Source: stakeholder-answers.md Q5.

### PRD-8: Registration with Claude Code

The server SHALL be registrable with
`claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`,
and the implementation MUST ship a project `.mcp.json` running the same command.

- WHEN `.mcp.json` is read THEN it declares `cli-tools` running `server.py`
  with `--root`.

Source: stakeholder-answers.md Q6.

## Non-goals

- Write operations (commit, checkout, push) and any CLI other than git and
  rg (Q1, Q7).
- HTTP or SSE transport, authentication, MCP resources or prompts (Q7).

## Open questions

None open. Resolved during review:

- "Git and stuff, whatever the team uses" → PRD-2 (git and rg, four tools).
- "Should be safe" / "nothing dangerous" → PRD-5 and PRD-6.
- "Needs to work with Claude Code" → PRD-1 and PRD-8.
