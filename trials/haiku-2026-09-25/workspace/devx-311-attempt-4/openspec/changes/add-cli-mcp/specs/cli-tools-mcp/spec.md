# Specification: CLI tools through MCP

## ADDED Requirements

### Requirement: Expose exactly four CLI tools

The MCP server SHALL expose exactly four tools: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`. The server SHALL use only two underlying CLIs: git and ripgrep (rg). No other CLIs, subcommands, or general shell execution SHALL be exposed.

Trace: PRD-1

#### Scenario: Tools list returns exactly four tools

- **WHEN** an MCP client calls `tools/list`
- **THEN** the server responds with exactly the four tools and their input schemas

#### Scenario: git_status executes

- **WHEN** Claude calls `git_status` in a git repository
- **THEN** the MCP server executes the git status command and returns results

#### Scenario: git_log executes with limit parameter

- **WHEN** Claude calls `git_log` with a limit parameter
- **THEN** the MCP server executes the git log command with the provided limit

#### Scenario: git_diff_stat executes

- **WHEN** Claude calls `git_diff_stat` in a git repository
- **THEN** the MCP server executes git diff --stat and returns results

#### Scenario: rg_search executes with pattern

- **WHEN** Claude calls `rg_search` with a pattern
- **THEN** the MCP server executes ripgrep with the provided pattern

#### Scenario: Unknown tool returns error -32602

- **WHEN** Claude calls any tool not in the four above
- **THEN** the MCP server returns JSON-RPC error -32602 (invalid params)

---

### Requirement: Communicate using MCP stdin/stdout protocol

The MCP server SHALL communicate over stdio using newline-delimited JSON-RPC 2.0, protocol version `2025-06-18`. The server SHALL implement the `tools/list` and `tools/call` MCP methods.

Trace: PRD-2

#### Scenario: MCP activation via claude mcp add command

- **WHEN** a developer runs `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`
- **THEN** Claude Code registers the MCP server for that project

#### Scenario: MCP activation via .mcp.json file

- **WHEN** a project `.mcp.json` file contains the server command
- **THEN** Claude Code activates the server on session start

#### Scenario: tools/list method returns schemas

- **WHEN** an MCP client calls the `tools/list` method
- **THEN** the server responds with a list of the four tools and their input schemas

---

### Requirement: Prevent shell injection and limit write operations

Commands SHALL run as argument lists with no shell interpretation. The server SHALL NOT expose any git write operations, including commit, checkout, and push. Patterns passed to `rg_search` that start with a dash (`-`) SHALL be treated as search patterns, not as flags.

Trace: PRD-3

#### Scenario: Pattern starting with dash is searched as literal

- **WHEN** Claude passes pattern `-v` to `rg_search` in a repository containing the string `-v`
- **THEN** the server returns results containing that literal string (not ripgrep's `-v` invert-match flag)

#### Scenario: Path with shell metacharacters is literal

- **WHEN** Claude passes a path containing shell metacharacters (e.g., `foo;rm`, `foo$(cmd)`) to `rg_search`
- **THEN** the server searches for files matching that path as a literal string (not interpreted by a shell)

#### Scenario: Write operations are not exposed

- **WHEN** Claude attempts to call a write operation such as `git_commit`, `git_checkout`, or `git_push`
- **THEN** the server does not expose such tools; calling them returns JSON-RPC error -32602

---

### Requirement: Enforce resource limits

Each command invocation SHALL timeout after 10 seconds. Output SHALL be truncated at 8000 characters with a `[truncated]` marker appended.

Trace: PRD-4

#### Scenario: Command timeout after 10 seconds

- **WHEN** a command runs longer than 10 seconds
- **THEN** the MCP server terminates it and returns `isError: true` with timeout as the reason

#### Scenario: Output truncated when exceeding 8000 characters

- **WHEN** a command produces output and the total would exceed 8000 characters
- **THEN** the server truncates to exactly 8000 characters and appends `[truncated]`

#### Scenario: Output exactly 8000 characters returns without marker

- **WHEN** a command produces exactly 8000 characters of output
- **THEN** the server returns all 8000 characters without the `[truncated]` marker

---

### Requirement: Define tool parameters and defaults

`git_log` SHALL accept a `limit` parameter as an integer in the range 1–50 with a default of 10. `rg_search` SHALL accept a required `pattern` parameter (non-empty string) and an optional `path` parameter with a default value of `.` (current directory). `git_status` and `git_diff_stat` SHALL accept no parameters.

Trace: PRD-5

#### Scenario: git_log without limit uses default 10

- **WHEN** `git_log` is called without a `limit` parameter in a repository with at least 10 commits
- **THEN** the tool returns exactly 10 log entries (the default limit)

#### Scenario: git_log with limit 1 returns 1 entry

- **WHEN** `git_log` is called with `limit: 1` in a repository with at least 1 commit
- **THEN** the tool returns exactly 1 log entry

#### Scenario: git_log with limit 50 returns 50 entries

- **WHEN** `git_log` is called with `limit: 50` in a repository with at least 50 commits
- **THEN** the tool returns exactly 50 log entries

#### Scenario: rg_search without path uses default current directory

- **WHEN** `rg_search` is called with `pattern: "TODO"` and no `path` parameter
- **THEN** it searches from the current directory (default `.`)

#### Scenario: rg_search with path searches that directory

- **WHEN** `rg_search` is called with `pattern: "TODO"` and `path: "src/"`
- **THEN** it searches within the `src/` directory

---

### Requirement: Enforce root directory and path boundaries

The MCP server SHALL run all commands in a root directory specified at startup via the `--root` flag. Paths passed to tools (e.g., `path` in `rg_search`) that resolve outside the root directory SHALL be rejected with a tool error stating the path escapes the root.

Trace: PRD-6

#### Scenario: Commands run in specified root directory

- **WHEN** the server is started with `--root /home/user/myrepo`
- **THEN** all commands execute with that as the working directory

#### Scenario: Relative path outside root is rejected

- **WHEN** `rg_search` is called with `path: "../other"` and the resolved path is outside `--root`
- **THEN** the server returns `isError: true` saying the path escapes the root

#### Scenario: Absolute path outside root is rejected

- **WHEN** `rg_search` is called with an absolute path outside `--root` (e.g., `path: "/etc/passwd"` while root is `/home/user/myrepo`)
- **THEN** the server returns `isError: true` saying the path escapes the root

---

### Requirement: Invoke ripgrep with literal pattern matching

The `rg_search` tool SHALL invoke ripgrep with the exact command line: `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`. The `-e` flag ensures the pattern is treated as a search pattern, and the `--` separator ensures the path is not interpreted as an option, even if it starts with a dash.

Trace: PRD-7

#### Scenario: Pattern passed with -e flag

- **WHEN** `rg_search` is called with a pattern
- **THEN** the server invokes ripgrep with the `-e` flag before the pattern

#### Scenario: Dash separator before path prevents option interpretation

- **WHEN** `rg_search` is called with both pattern and path
- **THEN** the server places `--` before the path to prevent path interpretation as an option

#### Scenario: rg_search invokes ripgrep with -e flag for dash patterns

- **WHEN** `rg_search` is called with `pattern: "-v"`
- **THEN** the server invokes ripgrep with the `-e -v` option to search for the literal string (not a flag)

---

### Requirement: Handle tool errors with isError flag and JSON-RPC error codes

When a tool invocation fails (bad argument, missing binary, non-zero exit, or timeout), the server SHALL return a normal JSON-RPC result with `isError: true` and include the reason as text. Protocol-level errors (unknown method, unparseable JSON) SHALL return standard JSON-RPC error codes. The exception is ripgrep exit code 1 (no matches), which SHALL be treated as a successful result.

Trace: PRD-8

#### Scenario: Tool failure returns isError flag

- **WHEN** a tool fails with a bad argument, missing binary, non-zero exit, or timeout
- **THEN** the server returns `isError: true` with the reason as text

#### Scenario: rg exit code 1 no matches is success

- **WHEN** `rg_search` exits with code 1 (no matches found)
- **THEN** the server returns a successful result (no error flag)

#### Scenario: Unknown tool name returns JSON-RPC error -32602

- **WHEN** Claude sends an unknown tool name
- **THEN** the server returns JSON-RPC error -32602

#### Scenario: Unknown method returns JSON-RPC error -32601

- **WHEN** Claude sends an unknown method
- **THEN** the server returns JSON-RPC error -32601

#### Scenario: Unparseable JSON returns JSON-RPC error -32700

- **WHEN** Claude sends unparseable JSON
- **THEN** the server returns JSON-RPC error -32700
