# Tasks

## 1. Protocol

- [x] 1.1 stdio loop: one JSON-RPC message per line, flush per response
- [x] 1.2 `initialize` (2025-06-18), `ping`, `tools/list`, `tools/call`
- [x] 1.3 Errors: -32602 unknown tool, -32601 unknown method, -32700 parse

## 2. Tools

- [x] 2.1 `git_status`, `git_diff_stat`
- [x] 2.2 `git_log` with `limit` 1–50, default 10
- [x] 2.3 `rg_search` with `-e <pattern> -- <path>`; exit 1 is "no matches"
- [x] 2.4 Reject unlisted arguments

## 3. Limits

- [x] 3.1 `--root` confinement
- [x] 3.2 No shell, 10 s timeout, 8000-character cap
- [x] 3.3 Missing binary, non-zero exit and timeout become `isError`

## 4. Registration

- [x] 4.1 `.mcp.json`
- [x] 4.2 `claude mcp add` documented

## 5. Verification

- [x] 5.1 One test per scenario, each naming its scenario
