# PRD — Give Claude CLI access through MCP (DEVX-311)

## Problem

Claude needs read-only access to repository inspection tools (git and ripgrep) through MCP to help developers analyze and understand repositories. Current workarounds require manual copying of tool output or Claude invoking arbitrary shell commands, which introduces security risks and friction.

## Users

Claude instances running within Claude Code environments, used by developers who need Claude to inspect repositories (viewing status, history, diffs, and searching files).

## Requirements

### PRD-1: Expose four read-only MCP tools only
The MCP server **SHALL** expose exactly four tools: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`. The server **SHALL NOT** expose a general shell, arbitrary git subcommands, or any write operations.

- WHEN Claude calls `tools/list`, THEN the server returns exactly four tools: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`.
- WHEN Claude attempts to run `git commit` or `git checkout`, THEN the tool is not available and Claude sees an error with code -32602 (unknown tool).

Source: interview.md Q1, Q2

### PRD-2: Restrict tool parameters to whitelisted arguments
The MCP server **SHALL** accept only the following parameters per tool and **SHALL** reject all others:
- `git_status`: no parameters
- `git_log`: `limit` (integer, 1–50, default 10)
- `git_diff_stat`: no parameters
- `rg_search`: `pattern` (required non-empty string) and `path` (optional, default `.`)

- WHEN Claude calls `rg_search` with `pattern="foo"` and `path="src/"`, THEN the search runs.
- WHEN Claude calls `rg_search` with `pattern="foo"` and `case_sensitive=true`, THEN the tool rejects the unknown `case_sensitive` parameter with an error.
- WHEN Claude calls `git_log` with `limit=1`, THEN it returns exactly 1 commit.
- WHEN Claude calls `git_log` with `limit=50`, THEN it returns up to 50 commits.
- WHEN Claude calls `git_log` with no `limit`, THEN it returns up to 10 commits (the default).

The server **SHALL** invoke `rg_search` using the command: `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`

Source: interview.md Q2, Q7

### PRD-3: Enforce 10-second timeout per command
Each tool invocation **SHALL** timeout after 10 seconds of execution.

- WHEN `rg_search` runs for 10 seconds without completing, THEN execution stops and Claude receives an error result with `isError: true` and an error message.
- WHEN `git_log` runs for 10 seconds without completing, THEN execution stops and Claude receives an error result with `isError: true` and an error message.
- WHEN `git_status` runs for 10 seconds without completing, THEN execution stops and Claude receives an error result with `isError: true` and an error message.
- WHEN `git_diff_stat` runs for 10 seconds without completing, THEN execution stops and Claude receives an error result with `isError: true` and an error message.

Source: interview.md Q2, Q5

### PRD-4: Truncate output at 8000 characters
Tool output **SHALL** be truncated at 8000 characters. If output exceeds this limit, the response **SHALL** include a `[truncated]` marker. This truncation applies to both successful results and error messages.

- WHEN `git_log` output exceeds 8000 characters, THEN the server returns the first 8000 characters followed by `[truncated]`.
- WHEN a tool produces an error message exceeding 8000 characters, THEN the server returns the first 8000 characters of the error message followed by `[truncated]`.

Source: interview.md Q2

### PRD-5: Return errors with isError flag and text explanation
When a tool invocation fails (bad argument, path outside root, missing binary, non-zero exit, or timeout), Claude **SHALL** receive a normal result with `isError: true` and a text explanation of the failure.

- WHEN `rg_search` is called with an invalid pattern, THEN Claude receives a result with `isError: true` and an error message.
- WHEN the root directory is not a valid git repository, THEN `git_status` returns a result with `isError: true` and an error message.

The server **SHALL** handle `rg` exit code 1 as a successful result, not an error. When `rg_search` exits with code 1, this indicates "no matches found," which is a normal completion.

- WHEN `rg_search` matches no files or patterns, THEN `rg` exits with code 1 and the server returns a successful result, not an error result.

Source: interview.md Q5, Q14

### PRD-6: Validate rg_search paths stay within configured root
The MCP server **SHALL** validate that the `path` argument in `rg_search` resolves to a location within the configured root directory. Paths that escape the root (e.g., `../`, absolute paths elsewhere) **SHALL** be rejected with a tool error.

- WHEN `rg_search` is called with `path="../etc/passwd"`, THEN the server rejects it with an error saying the path escapes the root.
- WHEN `rg_search` is called with `path="/etc/passwd"`, THEN the server rejects it with an error saying the path escapes the root.

Source: interview.md Q9

### PRD-7: Do not invoke shell; treat arguments as literal values
The MCP server **SHALL** run commands with argument lists and **SHALL NOT** invoke a shell. This means patterns and arguments **SHALL** be searched or used literally, not parsed as flags or interpreted by a shell.

- WHEN `rg_search` is called with `pattern="-v"`, THEN the literal string "-v" is searched, not interpreted as the "verbose" flag.
- WHEN `rg_search` is called with `pattern="foo; rm -rf /"`, THEN the literal string "foo; rm -rf /" is searched, not executed as a shell command.
- WHEN `rg_search` is called with `pattern="$VAR"`, THEN the literal string "$VAR" is searched, not expanded as a variable.

Source: interview.md Q2

### PRD-8: Configure root directory via --root flag at startup
The MCP server **SHALL** accept a `--root` flag at startup that specifies the root directory for all tool operations.

- WHEN the server starts with `--root /home/user/repo`, THEN all git and rg commands operate within `/home/user/repo`.

Source: interview.md Q6

### PRD-9: Support user-driven deployment via claude mcp add or .mcp.json
Users **SHALL** be able to configure the MCP server in two ways:
1. Running `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`
2. Creating a project `.mcp.json` file with the same command

Both methods **MUST** work.

- WHEN a user runs `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`, THEN Claude gains access to the four tools.
- WHEN a user creates a `.mcp.json` file with the same configuration, THEN Claude gains access to the four tools.

The server **SHALL NOT** be bundled by default with Claude Code.

Source: interview.md Q8

### PRD-10: Implement MCP protocol over stdio
The MCP server **SHALL** communicate using the MCP protocol version `2025-06-18` over **stdio** (standard input/output). The server **SHALL** respond to the following MCP methods: `initialize`, `ping`, `tools/list`, and `tools/call`. The server **SHALL** ignore MCP notifications.

- WHEN Claude connects to the MCP server, THEN the server communicates over stdio using protocol version `2025-06-18`.
- WHEN Claude calls `tools/list`, THEN the server responds with the four available tools.
- WHEN Claude calls an unknown method, THEN the server returns a JSON-RPC error with code **-32601**.
- WHEN Claude sends unparseable JSON, THEN the server returns a JSON-RPC error with code **-32700**.

JSON-RPC error codes:
- Unknown tool name: **-32602**
- Unknown method: **-32601**
- Unparseable JSON: **-32700**

Source: interview.md Q5

## Non-goals

The product owner explicitly declined to specify the following:

- **Success metrics:** How to measure whether Claude successfully uses the tools (Q3).
- **Environment scope:** Whether this must work across web app, CLI, and IDE extensions (Q4).
- **Output format:** Whether output is plain text, JSON, or structured (Q11).
- **Symlink handling:** How symlinks in the root or paths should be handled (Q12).
- **--root requirement:** Whether `--root` is mandatory or optional, and what the default is (Q13).
- **Timeout granularity:** Whether the 10-second timeout includes regex compilation or only execution (Q15).

## Open questions

Authentication is out of scope (Q10). The MCP server does not need to handle SSH keys, git credentials, or authentication configuration; it assumes the environment is already properly configured.
