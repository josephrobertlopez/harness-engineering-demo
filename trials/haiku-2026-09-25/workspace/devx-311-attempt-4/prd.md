# PRD — Give Claude our CLIs through MCP (DEVX-311)

## Problem

Claude has no access to git and ripgrep CLIs when working in Claude Code, forcing manual inspection of repository state and file content. A safe MCP server would let Claude run read-only git commands and text search directly.

## Users

Claude Code users (developers working in Claude Code IDE) needing to inspect repository history, current status, and search file contents.

## Requirements

### PRD-1: Expose four specific CLI tools from git and ripgrep

The MCP server SHALL use only two CLIs: `git` and `ripgrep` (rg). The server SHALL expose exactly four tools: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`. No other CLIs, subcommands, or general shell execution SHALL be exposed.

- WHEN Claude calls `tools/list` THEN the server returns exactly the four tools: `git_status`, `git_log`, `git_diff_stat`, `rg_search`
- WHEN Claude calls `git_status` THEN the MCP server executes the git status command
- WHEN Claude calls `git_log` THEN the MCP server executes the git log command with the provided limit
- WHEN Claude calls `git_diff_stat` THEN the MCP server executes git diff --stat
- WHEN Claude calls `rg_search` THEN the MCP server executes ripgrep with the provided pattern
- WHEN Claude calls any tool not in the four above THEN the MCP server returns JSON-RPC error -32602

Source: interview.md Q1, Q2

### PRD-2: Use MCP stdio protocol with JSON-RPC 2.0

The MCP server SHALL communicate over stdio using newline-delimited JSON-RPC 2.0, protocol version `2025-06-18`. The server SHALL implement the `tools/list` and `tools/call` MCP methods. The developer SHALL activate the server via `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo` or by adding the same command to a project `.mcp.json`.

- WHEN a developer runs `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo` THEN Claude Code registers the MCP server for that project
- WHEN the `.mcp.json` file contains the server command THEN Claude Code activates it on session start
- WHEN an MCP client calls `tools/list` THEN the server responds with the four tools and their schemas

Source: interview.md Q6

### PRD-3: Prevent shell injection and write operations

Commands SHALL run as argument lists with no shell interpretation. The server SHALL NOT expose any git write operations, including commit, checkout, and push. Patterns passed to `rg_search` that start with a dash (`-`) SHALL be treated as search patterns, not as flags.

- WHEN Claude passes a pattern starting with `-v` to `rg_search` in a repository containing the string `-v` THEN the server returns results containing that literal string, not ripgrep's `-v` (invert match) flag
- WHEN Claude passes a `path` containing shell metacharacters (e.g., `foo;rm`, `foo$(cmd)`) to `rg_search` THEN the server searches for files matching that path as a literal string, not interpreted by a shell
- WHEN Claude attempts to call a write operation such as git commit, git checkout, or git push THEN the server does not expose such tools; calling them returns JSON-RPC error -32602

Source: interview.md Q4

### PRD-4: Enforce resource limits

Each command invocation SHALL timeout after 10 seconds. Output SHALL be truncated at 8000 characters with a `[truncated]` marker appended.

- WHEN a command runs longer than 10 seconds THEN the MCP server terminates it and returns `isError: true` with timeout as the reason
- WHEN a command produces output and the total output length would exceed 8000 characters THEN the server truncates the output to exactly 8000 characters and appends `[truncated]`
- WHEN a command produces exactly 8000 characters of output THEN the server returns all 8000 characters without the `[truncated]` marker

Source: interview.md Q4

### PRD-5: Define tool parameters and defaults

`git_log` SHALL accept a `limit` parameter as an integer in the range 1–50 with a default of 10. `rg_search` SHALL accept a required `pattern` parameter (non-empty string) and an optional `path` parameter with a default value of `.` (current directory). `git_status` and `git_diff_stat` SHALL accept no parameters.

- WHEN `git_log` is called without a `limit` parameter in a repository with at least 10 commits THEN the tool returns exactly 10 log entries (the default limit)
- WHEN `git_log` is called with `limit: 1` in a repository with at least 1 commit THEN the tool returns exactly 1 log entry
- WHEN `git_log` is called with `limit: 50` in a repository with at least 50 commits THEN the tool returns exactly 50 log entries
- WHEN `rg_search` is called with `pattern: "TODO"` and no `path` THEN it searches from the current directory (default `.`)
- WHEN `rg_search` is called with `pattern: "TODO"` and `path: "src/"` THEN it searches within the `src/` directory

Source: interview.md Q8

### PRD-6: Set a fixed root directory and enforce path boundaries

The MCP server SHALL run all commands in a root directory specified at startup via the `--root` flag. Paths passed to tools (e.g., `path` in `rg_search`) that resolve outside the root directory SHALL be rejected with a tool error stating the path escapes the root.

- WHEN the server is started with `--root /home/user/myrepo` THEN all commands execute with that as the working directory
- WHEN `rg_search` is called with `path: "../other"` and the resolved path is outside `--root` THEN the server returns `isError: true` saying the path escapes the root
- WHEN `rg_search` is called with an absolute path outside `--root` (e.g., `path: "/etc/passwd"` while root is `/home/user/myrepo`) THEN the server returns `isError: true` saying the path escapes the root

Source: interview.md Q10

### PRD-7: Invoke ripgrep with literal pattern matching

The `rg_search` tool SHALL invoke ripgrep with the exact command line: `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`. The `-e` flag ensures the pattern is treated as a search pattern, and the `--` separator ensures the path is not interpreted as an option, even if it starts with a dash.

- WHEN `rg_search` is called with a pattern THEN the server invokes ripgrep with the `-e` flag before the pattern
- WHEN `rg_search` is called with both pattern and path THEN the server places `--` before the path to prevent path interpretation as an option
- WHEN `rg_search` is called with `pattern: "-v"` THEN the server searches for the literal string "-v" instead of parsing it as a ripgrep flag

Source: interview.md Q16

### PRD-8: Handle errors with `isError` flag and JSON-RPC errors

When a tool invocation fails (bad argument, missing binary, non-zero exit, or timeout), the server SHALL return a normal JSON-RPC result with `isError: true` and include the reason as text. Protocol-level errors (unknown method, unparseable JSON) SHALL return standard JSON-RPC error codes. The exception is ripgrep exit code 1 (no matches), which SHALL be treated as a successful result.

- WHEN a tool fails with a bad argument, missing binary, non-zero exit, or timeout THEN the server returns `isError: true` with the reason as text
- WHEN `rg_search` exits with code 1 (no matches) THEN the server returns a successful result (no error)
- WHEN Claude sends an unknown tool name THEN the server returns JSON-RPC error -32602
- WHEN Claude sends an unknown method THEN the server returns JSON-RPC error -32601
- WHEN Claude sends unparseable JSON THEN the server returns JSON-RPC error -32700

Source: interview.md Q7

## Non-goals

- Success metrics or performance benchmarks (Q3)
- Authorization or request validation (Q5)
- Truncation marker placement format (Q9)
- Output format for successful tool results (Q11)
- Argument validation at constraint boundaries (Q12)
- UTF-8 truncation boundary handling (Q13)
- Path type validation and non-existent path handling (Q14)
- Concurrency model for processing multiple requests (Q15)

## Open Questions

None. All material behavioral questions have been answered.
