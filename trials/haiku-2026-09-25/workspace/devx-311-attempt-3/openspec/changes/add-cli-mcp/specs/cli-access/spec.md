# Specification: CLI Access MCP Server

## ADDED Requirements

### Requirement: Expose four read-only MCP tools

The MCP server **SHALL** expose exactly four tools: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`. The server **SHALL NOT** expose a general shell, arbitrary git subcommands, or any write operations.

Trace: PRD-1

#### Scenario: tools/list returns four tools
- **WHEN** Claude calls `tools/list`
- **THEN** the server responds with exactly four tools: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`

#### Scenario: unknown tool returns error
- **WHEN** Claude attempts to call `git commit`
- **THEN** the server returns a JSON-RPC error with code -32602 (unknown tool)

---

### Requirement: Restrict tool parameters to whitelisted arguments

The MCP server **SHALL** accept only the following parameters per tool and **SHALL** reject all others:
- `git_status`: no parameters
- `git_log`: `limit` (integer, 1–50, default 10)
- `git_diff_stat`: no parameters
- `rg_search`: `pattern` (required non-empty string) and `path` (optional, default `.`)

The server **SHALL** invoke `rg_search` using the command: `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`

Trace: PRD-2

#### Scenario: rg_search with valid pattern and path
- **WHEN** Claude calls `rg_search` with `pattern="foo"` and `path="src/"`
- **THEN** the search executes and returns matching lines

#### Scenario: rg_search rejects unknown parameter
- **WHEN** Claude calls `rg_search` with `pattern="foo"` and `case_sensitive=true`
- **THEN** the server returns an error rejecting the unknown parameter

#### Scenario: git_log with limit=1
- **WHEN** Claude calls `git_log` with `limit=1`
- **THEN** the server returns exactly 1 commit

#### Scenario: git_log with limit=50
- **WHEN** Claude calls `git_log` with `limit=50`
- **THEN** the server returns up to 50 commits

#### Scenario: git_log with default limit
- **WHEN** Claude calls `git_log` with no `limit` parameter
- **THEN** the server returns up to 10 commits (the default)

#### Scenario: rg command invocation uses correct syntax
- **WHEN** the server invokes ripgrep for `rg_search`
- **THEN** it uses the command: `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`

---

### Requirement: Enforce 10-second timeout per command

Each tool invocation **SHALL** timeout after 10 seconds of execution.

Trace: PRD-3

#### Scenario: rg_search timeout
- **WHEN** `rg_search` runs for 10 seconds without completing
- **THEN** execution stops and Claude receives an error result with `isError: true`

#### Scenario: git_log timeout
- **WHEN** `git_log` runs for 10 seconds without completing
- **THEN** execution stops and Claude receives an error result with `isError: true`

#### Scenario: git_status timeout
- **WHEN** `git_status` runs for 10 seconds without completing
- **THEN** execution stops and Claude receives an error result with `isError: true`

#### Scenario: git_diff_stat timeout
- **WHEN** `git_diff_stat` runs for 10 seconds without completing
- **THEN** execution stops and Claude receives an error result with `isError: true`

---

### Requirement: Truncate output at 8000 characters

Tool output **SHALL** be truncated at 8000 characters. If output exceeds this limit, the response **SHALL** include a `[truncated]` marker. This truncation applies to both successful results and error messages.

Trace: PRD-4

#### Scenario: successful output truncation
- **WHEN** `git_log` output exceeds 8000 characters
- **THEN** the server returns the first 8000 characters followed by `[truncated]`

#### Scenario: error message truncation
- **WHEN** a tool produces an error message exceeding 8000 characters
- **THEN** the server returns the first 8000 characters of the error message followed by `[truncated]`

---

### Requirement: Return errors with isError flag and text explanation

When a tool invocation fails (bad argument, path outside root, missing binary, non-zero exit, or timeout), Claude **SHALL** receive a normal result with `isError: true` and a text explanation of the failure. The server **SHALL** handle `rg` exit code 1 (no matches found) as a successful result, not an error.

Trace: PRD-5

#### Scenario: invalid rg pattern error
- **WHEN** `rg_search` is called with an invalid pattern
- **THEN** Claude receives a result with `isError: true` and an error message

#### Scenario: git_status error for non-repository
- **WHEN** `git_status` is called and the root directory is not a valid git repository
- **THEN** the server returns a result with `isError: true` and an error message

#### Scenario: rg_search no matches is success
- **WHEN** `rg_search` matches no files or patterns and `rg` exits with code 1
- **THEN** the server returns a successful result, not an error result

---

### Requirement: Validate rg_search paths stay within configured root

The MCP server **SHALL** validate that the `path` argument in `rg_search` resolves to a location within the configured root directory. Paths that escape the root (e.g., `../`, absolute paths elsewhere) **SHALL** be rejected with a tool error.

Trace: PRD-6

#### Scenario: rg_search rejects path escape with ../
- **WHEN** `rg_search` is called with `path="../etc/passwd"`
- **THEN** the server rejects it with an error saying the path escapes the root

#### Scenario: rg_search rejects absolute path outside root
- **WHEN** `rg_search` is called with `path="/etc/passwd"`
- **THEN** the server rejects it with an error saying the path escapes the root

---

### Requirement: Do not invoke shell; treat arguments as literal values

The MCP server **SHALL** run commands with argument lists and **SHALL NOT** invoke a shell. This means patterns and arguments **SHALL** be searched or used literally, not parsed as flags or interpreted by a shell.

Trace: PRD-7

#### Scenario: pattern with dash is literal
- **WHEN** `rg_search` is called with `pattern="-v"`
- **THEN** the literal string "-v" is searched, not interpreted as the "verbose" flag

#### Scenario: pattern with semicolon is literal
- **WHEN** `rg_search` is called with `pattern="foo; rm -rf /"`
- **THEN** the literal string "foo; rm -rf /" is searched, not executed as a shell command

#### Scenario: pattern with variable syntax is literal
- **WHEN** `rg_search` is called with `pattern="$VAR"`
- **THEN** the literal string "$VAR" is searched, not expanded as a variable

---

### Requirement: Configure root directory via --root flag at startup

The MCP server **SHALL** accept a `--root` flag at startup that specifies the root directory for all tool operations.

Trace: PRD-8

#### Scenario: server accepts --root flag
- **WHEN** the server starts with `--root /home/user/repo`
- **THEN** the server initializes successfully

#### Scenario: all commands operate within root
- **WHEN** commands are executed after server startup with `--root /home/user/repo`
- **THEN** all git and rg operations occur within `/home/user/repo`

---

### Requirement: Support user-driven deployment via claude mcp add or .mcp.json

Users **SHALL** be able to configure the MCP server in two ways:
1. Running `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`
2. Creating a project `.mcp.json` file with the same command

Both methods **MUST** work. The server **SHALL NOT** be bundled by default with Claude Code.

Trace: PRD-9

#### Scenario: claude mcp add configuration works
- **WHEN** a user runs `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`
- **THEN** Claude gains access to the four tools

#### Scenario: .mcp.json configuration works
- **WHEN** a user creates a project `.mcp.json` file with the same configuration
- **THEN** Claude gains access to the four tools

---

### Requirement: Implement MCP protocol over stdio

The MCP server **SHALL** communicate using the MCP protocol version `2025-06-18` over **stdio** (standard input/output). The server **SHALL** respond to the following MCP methods: `initialize`, `ping`, `tools/list`, and `tools/call`. The server **SHALL** ignore MCP notifications.

JSON-RPC error codes:
- Unknown tool name: **-32602**
- Unknown method: **-32601**
- Unparseable JSON: **-32700**

Trace: PRD-10

#### Scenario: server communicates over stdio
- **WHEN** Claude connects to the MCP server
- **THEN** the server communicates over stdio using protocol version `2025-06-18`

#### Scenario: unknown method returns error
- **WHEN** Claude calls an unknown MCP method
- **THEN** the server returns a JSON-RPC error with code -32601

#### Scenario: unparseable JSON returns error
- **WHEN** Claude sends unparseable JSON
- **THEN** the server returns a JSON-RPC error with code -32700

#### Scenario: server responds to initialize
- **WHEN** Claude calls the `initialize` method
- **THEN** the server responds with protocol information and tool list

#### Scenario: server responds to ping
- **WHEN** Claude calls the `ping` method
- **THEN** the server responds successfully
