# CLI MCP Server Specification

## ADDED Requirements

### Requirement: MCP server exposes git and ripgrep tools

The MCP server SHALL expose tools from exactly two command-line tools: `git` and `rg` (ripgrep). No other CLIs are included.

Trace: PRD-1

#### Scenario: Server advertises git and ripgrep tools

- **WHEN** the server starts
- **THEN** only tools from `git` and `rg` are available to Claude

#### Scenario: Other CLIs are not exposed

- **WHEN** Claude requests a tool from tools outside {git, rg} (e.g., npm, docker, terraform)
- **THEN** the server returns error -32602 (unknown tool)

### Requirement: Four read-only tools are available

The server SHALL expose exactly four tools, all read-only: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`. No write operations like push, commit, or checkout are exposed.

Trace: PRD-2

#### Scenario: Four tools are available

- **WHEN** Claude invokes one of {`git_status`, `git_log`, `git_diff_stat`, `rg_search`}
- **THEN** the server executes the corresponding command and returns output

#### Scenario: Write operations are not available

- **WHEN** Claude attempts to invoke a write operation like `git_push`, `git_commit`, or `git_checkout`
- **THEN** the server returns error -32602 (unknown tool)

### Requirement: git_log command signature

The `git_log` tool SHALL execute `git log --oneline -n <limit>`, where `limit` is an integer parameter (1–50, default 10).

Trace: PRD-3

#### Scenario: git_log with explicit limit

- **WHEN** Claude calls `git_log` with `limit=5`
- **THEN** the server runs `git log --oneline -n 5`

#### Scenario: git_log with default limit

- **WHEN** Claude calls `git_log` without a `limit` parameter
- **THEN** the server runs `git log --oneline -n 10`

### Requirement: git_diff_stat command has no parameters

The `git_diff_stat` tool SHALL execute `git diff --stat` exactly, with no parameters or options accepted.

Trace: PRD-4

#### Scenario: git_diff_stat accepts no parameters

- **WHEN** Claude calls `git_diff_stat`
- **THEN** the server runs `git diff --stat` with no additional arguments

### Requirement: rg_search command signature

The `rg_search` tool SHALL execute `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`, where `pattern` is a required non-empty string and `path` is optional (default `.`).

Trace: PRD-5

#### Scenario: rg_search with pattern and path

- **WHEN** Claude calls `rg_search` with `pattern="TODO"` and `path="src/"`
- **THEN** the server runs `rg --line-number --no-heading --color never --max-count 50 -e TODO -- src/`

#### Scenario: rg_search with default path

- **WHEN** Claude calls `rg_search` with only `pattern="TODO"`
- **THEN** the server runs `rg --line-number --no-heading --color never --max-count 50 -e TODO -- .`

### Requirement: Shell injection prevention

All commands SHALL run as argument arrays without shell interpretation. Shell metacharacters in arguments (|, ;, $, `, etc.) SHALL NOT be interpreted as shell syntax.

Trace: PRD-6

#### Scenario: Shell metacharacters are not interpreted

- **WHEN** Claude calls `rg_search` with `pattern="$(rm -rf /)"`
- **THEN** the pattern is passed literally to ripgrep without shell execution

#### Scenario: Command path injection is prevented

- **WHEN** Claude calls a tool with arguments containing shell metacharacters like `; cat /etc/passwd`
- **THEN** those characters are passed as literal argument values, not executed by a shell

#### Scenario: Path traversal characters are not shell-evaluated

- **WHEN** Claude calls `rg_search` with `path="../../../etc/passwd"`
- **THEN** the path string is passed literally to rg; path validation (PRD-12/13) determines if it's allowed

### Requirement: 10-second timeout per invocation

Each tool invocation SHALL time out after 10 seconds of execution.

Trace: PRD-7

#### Scenario: Tool execution times out after 10 seconds

- **WHEN** a tool runs longer than 10 seconds
- **THEN** execution is terminated and an error is returned

### Requirement: Output is limited to 8000 characters

All tool output SHALL be limited to 8000 characters. When output exceeds this limit, it SHALL be truncated silently at 8000 characters and `[truncated]` appended.

Trace: PRD-8

#### Scenario: Output under 8000 characters is returned in full

- **WHEN** a tool produces 5000 characters of output
- **THEN** the full 5000 characters are returned without a marker

#### Scenario: Output at exactly 8000 characters is returned without marker

- **WHEN** a tool produces exactly 8000 characters of output
- **THEN** all 8000 characters are returned without `[truncated]` marker

#### Scenario: Output over 8000 characters is truncated and marked

- **WHEN** a tool produces 8500 characters of output
- **THEN** the output is cut at 8000 characters and `[truncated]` is appended

### Requirement: Failed tools return error with reason

When a tool fails (command error, timeout, or other failure), the server SHALL return a result object with `isError: true` and the reason as plain text.

Trace: PRD-9

#### Scenario: Tool failure includes error reason

- **WHEN** a tool execution fails
- **THEN** the result contains `{isError: true, reason: "<error description>"}`

### Requirement: Ripgrep exit code 1 is not an error

When `rg_search` finds no matching lines, ripgrep exits with code 1. The server SHALL treat this as a successful result (no matches found), not as a tool error.

Trace: PRD-10

#### Scenario: ripgrep exit 1 returns normal result

- **WHEN** `rg_search` executes and ripgrep exits with code 1 (no matches)
- **THEN** the server returns a normal result with empty content

#### Scenario: ripgrep exit 1 does not set isError

- **WHEN** `rg_search` completes with ripgrep exit code 1
- **THEN** `isError` is NOT set to true

#### Scenario: Other ripgrep exit codes are errors

- **WHEN** ripgrep exits with code 2 (error)
- **THEN** the server returns `isError: true` with the error reason

### Requirement: Unknown tools return JSON-RPC error -32602

When Claude attempts to invoke a tool not in {`git_status`, `git_log`, `git_diff_stat`, `rg_search`}, the server SHALL return JSON-RPC error code -32602 (unknown tool name).

Trace: PRD-11

#### Scenario: Unknown tool returns -32602

- **WHEN** Claude requests an unknown tool like `git_push`
- **THEN** the server returns JSON-RPC error -32602

#### Scenario: Write operation returns -32602

- **WHEN** Claude attempts any write operation like `git_commit`
- **THEN** the server returns JSON-RPC error -32602

### Requirement: Root directory constrains accessible paths

The server SHALL be initialized with a `--root` directory (fixed at startup) that constrains what paths tools can access. Any path parameter that resolves outside the root SHALL be rejected with a tool error.

Trace: PRD-12

#### Scenario: Root directory constraint is enforced

- **WHEN** the server is invoked with `--root /abs/path/to/repo`
- **THEN** all path operations are validated against this root directory

### Requirement: Paths outside root are rejected

The server MUST reject paths that escape the root directory. When tools receive a path argument that resolves outside the `--root` directory (e.g., `../../../etc/passwd`), the server SHALL return a tool error with the message "path escapes the root".

Trace: PRD-13

#### Scenario: Path traversal is rejected

- **WHEN** Claude calls `rg_search` with `path="../../../etc/passwd"` and `--root=/repo`
- **THEN** the server validates the resolved path and returns an error "path escapes the root"

#### Scenario: Absolute paths outside root are rejected

- **WHEN** Claude provides an absolute path like `/etc/passwd` that resolves outside `--root`
- **THEN** the server returns error "path escapes the root"

### Requirement: MCP protocol uses stdio with JSON-RPC 2.0

The MCP server SHALL communicate using newline-delimited JSON-RPC 2.0 over stdin/stdout (stdio).

Trace: PRD-14

#### Scenario: Server listens on stdin for JSON-RPC requests

- **WHEN** the server starts
- **THEN** it listens on stdin for newline-delimited JSON-RPC messages

#### Scenario: Server sends JSON-RPC responses on stdout

- **WHEN** a valid JSON-RPC request is received
- **THEN** the server writes a newline-delimited JSON-RPC response to stdout

### Requirement: MCP protocol version is 2025-06-18

The server SHALL implement MCP protocol version `2025-06-18`.

Trace: PRD-15

#### Scenario: Server advertises protocol version

- **WHEN** the MCP client initiates a connection or queries the protocol version
- **THEN** the server advertises protocol version `2025-06-18`

### Requirement: Parse errors return JSON-RPC error -32700

When the MCP client sends malformed JSON-RPC (unparseable JSON), the server SHALL return JSON-RPC error code -32700.

Trace: PRD-16

#### Scenario: Unparseable JSON returns -32700

- **WHEN** the client sends invalid or truncated JSON on stdin
- **THEN** the server returns JSON-RPC error -32700

#### Scenario: Binary data returns -32700

- **WHEN** the client sends binary data that cannot be parsed as JSON
- **THEN** the server returns JSON-RPC error -32700

### Requirement: Server registration supports two methods

The server SHALL be registrable with Claude Code via two methods:
1. Command-line: `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`
2. Project configuration: A `.mcp.json` file with the same command

Trace: PRD-17

#### Scenario: CLI registration works

- **WHEN** a user runs `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`
- **THEN** the server is registered and available to Claude Code

#### Scenario: Project configuration registration works

- **WHEN** a project contains a `.mcp.json` file with the server command
- **THEN** the server is registered and available from that project
