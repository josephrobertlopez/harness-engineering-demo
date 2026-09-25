# PRD — Give Claude our CLIs through MCP (DEVX-311)

## Problem

Claude needs read-only access to repository data and code search capabilities so it can understand and analyze repositories. The platform previously attempted an overly-permissive shell command MCP server that created safety issues; this design must prevent similar risks while providing useful repository inspection tools.

## Users

Claude (the AI model running in Claude Code or other products) needs to inspect repository state, history, and search code within repositories.

## Requirements

### PRD-1: MCP server exposes exactly two CLIs

The MCP server SHALL expose tools from exactly two command-line tools: `git` and `rg` (ripgrep). No other CLIs are included.

- WHEN the server starts, THEN only git and ripgrep tools are available to Claude
- Source: interview.md Q1

### PRD-2: Four read-only tools are available

The server SHALL expose exactly four tools, all read-only, with no write operations:

1. `git_status`
2. `git_log` with a `limit` parameter (integer, 1–50, default 10)
3. `git_diff_stat` with no parameters
4. `rg_search` with a `pattern` parameter (required non-empty string) and optional `path` parameter (default `.`)

- WHEN Claude invokes one of these four tools, THEN it receives output from the corresponding command
- WHEN Claude attempts any write operation like push, commit, or checkout, THEN it is not available
- Source: interview.md Q2, Q8, Q11

### PRD-3: git_log command signature is fixed

The `git_log` tool SHALL execute the command `git log --oneline -n <limit>`, where `limit` is the sole parameter provided by Claude (integer 1–50, default 10).

- WHEN Claude calls `git_log` with limit=5, THEN the server runs `git log --oneline -n 5`
- WHEN Claude calls `git_log` without a limit, THEN the server runs `git log --oneline -n 10`
- Source: interview.md Q8

### PRD-4: git_diff_stat command has no parameters

The `git_diff_stat` tool SHALL execute the command `git diff --stat` exactly, with no parameters or options.

- WHEN Claude calls `git_diff_stat`, THEN the server runs `git diff --stat`
- WHEN Claude attempts to pass parameters to `git_diff_stat`, THEN the parameters are ignored
- Source: interview.md Q11

### PRD-5: rg_search command signature is fixed

The `rg_search` tool SHALL execute the command `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`, where `pattern` is a required non-empty string and `path` is an optional string (default `.`).

- WHEN Claude calls `rg_search` with pattern="TODO" and path="src/", THEN the server runs `rg --line-number --no-heading --color never --max-count 50 -e TODO -- src/`
- WHEN Claude calls `rg_search` with only pattern="TODO", THEN the server runs `rg --line-number --no-heading --color never --max-count 50 -e TODO -- .`
- Source: interview.md Q8

### PRD-6: Commands run without shell interpretation; injection is prevented

All commands SHALL run as argument lists without invoking a shell, preventing shell metacharacters (|, ;, $, `, &, >, <, (, ), {, }, [, ], \) in arguments from being interpreted as shell commands. Argument injection SHALL be prevented by protecting user-supplied arguments with appropriate escaping or quoting mechanisms.

- WHEN a tool is invoked with arguments, THEN shell metacharacters in arguments are not interpreted as shell syntax
- WHEN `rg_search` pattern contains shell metacharacters like `$(rm -rf /)`, THEN those characters are passed literally to ripgrep, not executed as shell commands
- WHEN `rg_search` path contains `..` or `/`, THEN the path is validated by PRD-12/13, not evaluated by a shell
- Source: interview.md Q4

### PRD-7: Commands have a 10-second timeout

Each tool invocation SHALL time out after 10 seconds of execution.

- WHEN a tool runs longer than 10 seconds, THEN execution is terminated
- Source: interview.md Q4

### PRD-8: Output is limited to 8000 characters

All tool output SHALL be limited to 8000 characters. When output exceeds this limit, it SHALL be truncated silently at 8000 characters and a `[truncated]` marker appended.

- WHEN a tool produces more than 8000 characters, THEN the output is cut at 8000 characters and `[truncated]` is appended
- WHEN a tool produces exactly 8000 characters or fewer, THEN the full output is returned without a marker
- WHEN output is truncated, THEN `isError` is NOT set to true; this is not treated as an error
- Source: interview.md Q4, Q12

### PRD-9: Failed tools return isError with reason text

When a tool fails (due to command error, timeout, or any other failure), the server SHALL return a normal result object with `isError: true` and the reason as plain text.

- WHEN a tool execution fails, THEN the result contains `{isError: true, reason: "<error reason text>"}`
- WHEN Claude reads an error result, THEN it can adapt based on the human-readable reason text
- Source: interview.md Q7

### PRD-10: Ripgrep exit status 1 means no matches found, which is not an error

When `rg_search` is executed and ripgrep finds no matching lines, ripgrep terminates with exit code 1. The server SHALL treat exit code 1 as a success case (no matches found), not as a tool error. The server SHALL return output as empty content without setting `isError: true`.

- WHEN `rg_search` executes and finds no matching lines, THEN ripgrep exits with code 1
- WHEN the `rg_search` tool receives exit code 1 from ripgrep, THEN it returns a normal result (not an error result)
- WHEN a result has `isError: true`, THEN the exit code must have been something other than 0 or 1
- Source: interview.md Q21

### PRD-11: Unknown tools return JSON-RPC error -32602

When Claude or a user attempts to invoke a tool that is not one of the four specified tools, the server SHALL return JSON-RPC error code -32602 (unknown tool name).

- WHEN `git_push` or any tool name not in {`git_status`, `git_log`, `git_diff_stat`, `rg_search`} is requested, THEN the server returns JSON-RPC error -32602
- WHEN a write operation like `git_push` is attempted, THEN error -32602 is returned
- Source: interview.md Q5

### PRD-12: Root directory constrains accessible paths

The server SHALL be initialized with a `--root` directory that is fixed at startup. This directory serves as a constraint on what paths can be accessed by the tools: any `path` parameter that resolves outside the root SHALL be rejected with a tool error.

- WHEN the server is invoked with `--root /abs/path/to/repo`, THEN all path operations are constrained to this directory
- WHEN a tool is invoked with a path parameter, THEN the resolved path is validated against the root
- Source: interview.md Q22

### PRD-13: Paths outside the root directory are rejected

The server MUST reject paths that escape the root directory. When `rg_search` or other tools receive a `path` argument that resolves outside the `--root` directory (e.g., `../../../etc/passwd`), the server SHALL return a tool error indicating the path escapes the root.

- WHEN Claude provides a path like `../../../etc/passwd`, THEN the server validates the resolved path
- WHEN the resolved path is outside the root, THEN the server returns a tool error with the message "path escapes the root"
- Source: interview.md Q23

### PRD-14: MCP protocol uses stdio with newline-delimited JSON-RPC 2.0

The MCP server SHALL communicate using newline-delimited JSON-RPC 2.0 over stdin/stdout (stdio).

- WHEN the server starts, THEN it listens on stdin for newline-delimited JSON-RPC messages
- WHEN a request is processed, THEN the response is written to stdout as a newline-delimited JSON-RPC message
- Source: interview.md Q24

### PRD-15: MCP protocol version is 2025-06-18

The server SHALL implement MCP protocol version `2025-06-18`.

- WHEN the MCP client initiates a connection, THEN the server advertises protocol version `2025-06-18`
- Source: interview.md Q24

### PRD-16: Parse errors return JSON-RPC error -32700

When the MCP client sends malformed JSON-RPC (unparseable JSON), the server SHALL return a JSON-RPC 2.0 error response with error code -32700, formatted as: `{"jsonrpc": "2.0", "error": {"code": -32700, "message": "<error description>"}, "id": null}` (or with the request id if available).

- WHEN the client sends invalid or unparseable JSON on stdin, THEN the server responds with JSON-RPC error code -32700
- WHEN the server receives truncated JSON or binary data, THEN it returns error -32700
- Source: interview.md Q25

### PRD-17: Server registration supports two methods

The server SHALL be registrable with Claude Code via either of two methods:

1. Command-line registration: `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`
2. Project configuration: a `.mcp.json` file in the project containing the same command

- WHEN a user runs `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`, THEN the server is registered and available
- WHEN a project contains a `.mcp.json` file with the server command, THEN the server is registered and available
- Source: interview.md Q26

## Non-goals

The following are explicitly non-goals and out of scope for this task:

- **Platform/product target**: Which Claude products (Claude Code CLI, web app, IDE extensions, etc.) this should work with is not specified.
- **Acceptance testing criteria**: How to verify that "tools show up in Claude" is not defined.
- **MCP schema descriptions**: The text descriptions of tools in the MCP schema definition is not specified.
- **Unusual repository states**: How the server behaves when a repo is in the middle of a merge, rebase, or cherry-pick is not specified.
- **Test suite and validation**: Whether to include unit tests, integration tests, MCP schema validation, or other testing is not specified.
- **git_status output format**: Whether `git_status` output is raw git output or structured/formatted is not specified.
- **Non-git repository handling**: What the server should do if the `--root` path is not a git repository is not specified.

## Open questions

These questions were resolved during the interview:

- "should be safe" → PRD-6, PRD-7, PRD-8, PRD-11, PRD-12, PRD-13 (security constraints: no shell, timeout, output limit, restricted tools, path validation)
- "it can run git etc" → PRD-2 (four specific read-only tools from git and rg)
- "nothing dangerous" → PRD-6, PRD-7, PRD-8, PRD-11, PRD-12, PRD-13 (concrete safety constraints and path traversal protection)
- "needs to work with Claude Code" → PRD-17 (registration methods for Claude Code)
- "tools show up in Claude" → PRD-17 (registration mechanism enables tools to appear)
