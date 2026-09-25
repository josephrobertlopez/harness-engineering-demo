# OpenSpec Delta — cli-mcp

## ADDED Requirements

### Requirement: Available tools

The MCP server SHALL expose exactly four tools to Claude via the MCP protocol, named in snake_case: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`. These tools wrap two underlying CLIs: `git` (restricted to three read-only operations) and `rg` (ripgrep, restricted to pattern search). No other CLIs, shell commands, or general-purpose tool invocation SHALL be available.

Trace: PRD-1

#### Scenario: tool_invocation_succeeds

- **WHEN** Claude invokes a valid tool name (`git_status`, `git_log`, `git_diff_stat`, or `rg_search`)
- **THEN** the server dispatches to the corresponding tool handler and returns a result

#### Scenario: unknown_tool_rejected

- **WHEN** Claude invokes an MCP call for a tool that does not exist
- **THEN** the server returns MCP error code `-32602`

#### Scenario: invalid_tool_type

- **WHEN** Claude attempts to invoke any other tool, shell command, or CLI not in the whitelist
- **THEN** it receives an error via the error handling mechanism (PRD-12)

---

### Requirement: No shell execution

Commands MUST run as argument lists with no shell invocation ever. This prevents shell metacharacters, environment variable expansion, and command chaining. Arguments MUST be passed directly to the underlying command as an array, never parsed by a shell.

Trace: PRD-2

#### Scenario: arguments_as_array

- **WHEN** Claude provides arguments to any tool
- **THEN** they are passed as an argument list (array), never through a shell interpreter

#### Scenario: shell_metacharacters_literal

- **WHEN** Claude provides shell metacharacters (e.g., `|`, `>`, `;`, `$`, backtick)
- **THEN** they are treated as literal strings in the command arguments, not executed by a shell

#### Scenario: no_environment_expansion

- **WHEN** Claude provides arguments containing environment variable references (e.g., `$HOME`)
- **THEN** they are treated as literal strings, not expanded by the shell

---

### Requirement: Read-only operations

All operations MUST be read-only. Write operations MUST be forbidden, and git operations MUST not modify the repository. No files SHALL be created, modified, or deleted by any tool invocation.

Trace: PRD-3

#### Scenario: git_operations_readonly

- **WHEN** Claude invokes any git tool (`git_status`, `git_log`, `git_diff_stat`)
- **THEN** no files are created, modified, or deleted in the repository

#### Scenario: write_operations_fail

- **WHEN** Claude attempts a write operation through git (e.g., via a tool with write side effects)
- **THEN** the operation fails with `isError: true`

---

### Requirement: Timeout enforcement

Each underlying command execution (git or rg process) MUST have a maximum execution time of 10 seconds. Invocations exceeding this limit MUST be forcibly terminated and reported as errors. Whether partial output is captured before termination is not specified (see Non-goals in PRD).

Trace: PRD-4

#### Scenario: command_completes_under_timeout

- **WHEN** a command completes in less than 10 seconds
- **THEN** the result is returned normally with the command output

#### Scenario: command_timeout_10_seconds

- **WHEN** a git or rg command runs longer than 10 seconds
- **THEN** the process is forcibly terminated

#### Scenario: timeout_error_response

- **WHEN** a command times out after 10 seconds
- **THEN** the result includes `isError: true` and a reason string indicating timeout

---

### Requirement: Output truncation

Output from any tool MUST be truncated at 8000 characters (counted as Unicode characters, not bytes). If truncation occurs, the output MUST end with the marker `[truncated]`.

Trace: PRD-5

#### Scenario: output_under_limit

- **WHEN** a command produces 8000 characters or fewer
- **THEN** output is not truncated and is returned in full

#### Scenario: output_at_boundary

- **WHEN** a command produces exactly 8000 characters
- **THEN** output is returned in full without truncation

#### Scenario: output_exceeds_limit

- **WHEN** a command produces more than 8000 characters of output
- **THEN** output is cut at 8000 Unicode characters

#### Scenario: truncation_marker_appended

- **WHEN** output exceeds 8000 characters and is truncated
- **THEN** the result ends with the literal string `[truncated]`

---

### Requirement: Root directory isolation

The server MUST run within a root directory fixed at startup via the `--root` flag. All path arguments MUST be validated to ensure they do not escape this root. Paths that would escape the root MUST be rejected with an error.

Trace: PRD-6

#### Scenario: path_within_root

- **WHEN** Claude provides a path argument that stays within the root directory
- **THEN** it is accepted and the command operates on that path

#### Scenario: path_escape_parent_directory

- **WHEN** a path would escape the root via parent directory traversal (e.g., `../../../etc`)
- **THEN** the command fails with `isError: true` and a reason string indicating path is outside root

#### Scenario: absolute_path_rejected

- **WHEN** Claude provides an absolute path (e.g., `/etc/passwd`)
- **THEN** the command fails with `isError: true` indicating path must be relative to root

---

### Requirement: git_status operation

The `git_status` tool MUST accept no arguments and MUST invoke `git status --porcelain=v1 --branch`. It returns the short-form status of the working directory.

Trace: PRD-7

#### Scenario: git_status_no_arguments

- **WHEN** Claude invokes `git_status` with no arguments
- **THEN** it runs `git status --porcelain=v1 --branch` and returns the result

#### Scenario: git_status_with_arguments_fails

- **WHEN** Claude provides any arguments to `git_status`
- **THEN** the operation fails with `isError: true`

#### Scenario: git_status_in_git_repo

- **WHEN** Claude invokes `git_status` in a valid git repository
- **THEN** it returns porcelain-format output showing working directory status

#### Scenario: git_status_not_in_git_repo

- **WHEN** Claude invokes `git_status` in a directory that is not a git repository
- **THEN** it fails with `isError: true` and a reason indicating not a git repository

---

### Requirement: git_log operation

The `git_log` tool MUST accept one optional argument, `limit`, which MUST be an integer from 1 to 50 with a default of 10. It MUST invoke `git log --oneline -n <limit>`. Any non-integer or out-of-range value MUST be rejected with an error.

Trace: PRD-8

#### Scenario: git_log_default_limit

- **WHEN** Claude invokes `git_log` without arguments
- **THEN** it runs `git log --oneline -n 10`

#### Scenario: git_log_valid_limit_1

- **WHEN** Claude invokes `git_log` with `limit=1`
- **THEN** it runs `git log --oneline -n 1`

#### Scenario: git_log_valid_limit_50

- **WHEN** Claude invokes `git_log` with `limit=50`
- **THEN** it runs `git log --oneline -n 50`

#### Scenario: git_log_invalid_limit_below_range

- **WHEN** Claude provides a `limit` of 0 or less
- **THEN** the operation fails with `isError: true` and a reason indicating limit must be at least 1

#### Scenario: git_log_invalid_limit_above_range

- **WHEN** Claude provides a `limit` greater than 50
- **THEN** the operation fails with `isError: true` and a reason indicating limit must not exceed 50

#### Scenario: git_log_non_integer_limit

- **WHEN** Claude provides a non-integer `limit` (string, float, null)
- **THEN** the operation fails with `isError: true` and a reason indicating limit must be an integer

#### Scenario: git_log_in_non_git_repo

- **WHEN** Claude invokes `git_log` in a directory that is not a git repository
- **THEN** it fails with `isError: true` and a reason indicating not a git repository

---

### Requirement: git_diff_stat operation

The `git_diff_stat` tool MUST accept no arguments and MUST invoke `git diff --stat`. It returns a summary of changes in the working directory.

Trace: PRD-9

#### Scenario: git_diff_stat_no_arguments

- **WHEN** Claude invokes `git_diff_stat` with no arguments
- **THEN** it runs `git diff --stat` and returns the result

#### Scenario: git_diff_stat_with_arguments_fails

- **WHEN** Claude provides any arguments to `git_diff_stat`
- **THEN** the operation fails with `isError: true`

#### Scenario: git_diff_stat_with_changes

- **WHEN** Claude invokes `git_diff_stat` in a working directory with staged or unstaged changes
- **THEN** it returns diff stat summary of those changes

#### Scenario: git_diff_stat_no_changes

- **WHEN** Claude invokes `git_diff_stat` in a clean working directory
- **THEN** it returns empty output (no changes)

#### Scenario: git_diff_stat_not_in_git_repo

- **WHEN** Claude invokes `git_diff_stat` in a directory that is not a git repository
- **THEN** it fails with `isError: true` and a reason indicating not a git repository

---

### Requirement: rg_search operation

The `rg_search` tool MUST accept a pattern argument (required) and a path argument (optional, defaults to `.`). The server MUST invoke ripgrep with the exact flag sequence: `rg -e <pattern> -- <path>`, where the pattern is passed after `-e` and before `--`. All other ripgrep flags (`--line-number`, `--no-heading`, `--color never`, `--max-count 50`) are fixed by the implementation and not exposed to Claude. Any argument not in the pattern or path parameters MUST be rejected. This command structure prevents flag injection: patterns beginning with `-` are treated as literal search strings because they are passed after `-e` and before `--`.

Trace: PRD-10

#### Scenario: rg_search_pattern_only

- **WHEN** Claude invokes `rg_search` with pattern `foo`
- **THEN** the server runs `rg --line-number --no-heading --color never --max-count 50 -e foo -- .` from the root directory

#### Scenario: rg_search_pattern_and_path

- **WHEN** Claude invokes `rg_search` with pattern `foo` and path `src/`
- **THEN** the server runs `rg --line-number --no-heading --color never --max-count 50 -e foo -- src/`

#### Scenario: rg_search_pattern_with_dash

- **WHEN** Claude provides a pattern beginning with `-` (e.g., pattern `-v`)
- **THEN** it is treated as a literal search string: `rg ... -e -v -- .`

#### Scenario: rg_search_no_matches

- **WHEN** `rg_search` completes with no matches (ripgrep exit code 1)
- **THEN** the result is `{isError: false}` with empty output

#### Scenario: rg_search_with_matches

- **WHEN** `rg_search` finds matches
- **THEN** the result includes matched lines with line numbers (from `--line-number`)

#### Scenario: rg_search_invalid_flags

- **WHEN** Claude provides any additional arguments or flags beyond pattern and path
- **THEN** the operation fails with `isError: true`

#### Scenario: rg_search_output_truncated

- **WHEN** `rg_search` returns more than 8000 characters
- **THEN** output is truncated at 8000 characters and ends with `[truncated]`

---

### Requirement: Default search path

When `rg_search` is invoked without a path argument, it MUST default to `.`. Since all commands execute in the root directory specified by `--root`, the default `.` means the search starts from that root directory.

Trace: PRD-11

#### Scenario: rg_search_default_path

- **WHEN** Claude invokes `rg_search` with only a pattern argument
- **THEN** the search scans files starting from the root directory (`.`)

---

### Requirement: Tool-level error handling

Any tool invocation that fails—due to bad arguments, path escaping attempts, missing binary, non-zero exit code, or timeout—MUST return a result with `isError: true` and a reason string in plain text. Tool-level errors are distinct from MCP protocol-level errors (see Requirement: MCP protocol-level error codes). Exception: `rg` exit code 1 (no matches found) MUST be treated as a successful result, not an error.

Trace: PRD-12

#### Scenario: error_missing_binary

- **WHEN** a tool is invoked but the underlying binary (git or rg) is not installed
- **THEN** the result is `{isError: true, reason: "<reason indicating binary not found>"}`

#### Scenario: error_timeout

- **WHEN** a tool times out after 10 seconds
- **THEN** the result is `{isError: true, reason: "<reason indicating timeout>"}`

#### Scenario: error_path_escape

- **WHEN** a path argument escapes the root directory
- **THEN** the result is `{isError: true, reason: "<reason indicating path outside root>"}`

#### Scenario: rg_no_matches_success

- **WHEN** `rg_search` completes with exit code 1 (no matches)
- **THEN** the result is `{isError: false}` with empty output, not an error

---

### Requirement: Platform integration

The MCP server MUST operate over stdio and be compatible with Claude Code. It SHALL work with Claude Code's MCP integration via standard input/output. Commands are executed within the context of the root directory and communicate results through the MCP protocol.

Trace: PRD-13

#### Scenario: mcp_stdio_communication

- **WHEN** Claude Code starts the MCP server
- **THEN** it communicates via stdio using the MCP protocol

#### Scenario: mcp_tool_invocation

- **WHEN** Claude Code invokes a tool through MCP
- **THEN** the MCP protocol is used over stdio to send the request and receive the response

---

### Requirement: MCP protocol version

The server MUST implement and advertise MCP protocol version `2025-06-18` in the MCP initialize response.

Trace: PRD-14

#### Scenario: mcp_initialize_version

- **WHEN** Claude Code initiates an MCP initialize handshake
- **THEN** the server responds with protocol version `2025-06-18`

#### Scenario: mcp_protocol_compatibility

- **WHEN** the server starts
- **THEN** it is compatible with MCP protocol version `2025-06-18`

---

### Requirement: MCP protocol-level error codes

The server MUST return MCP-standard error codes for protocol-level failures that occur before tool invocation. These are distinct from tool-level errors (see Requirement: Tool-level error handling). The server MUST return: `-32602` for unknown tool name, `-32601` for unknown method, and `-32700` for unparseable JSON. Tool-level errors (bad arguments, missing binary, path escape attempts, command timeout) use the tool-level error handling mechanism instead.

Trace: PRD-15

#### Scenario: mcp_error_unknown_tool

- **WHEN** Claude invokes an MCP call for a tool that does not exist (e.g., `nonexistent_tool`)
- **THEN** the server returns MCP error code `-32602`

#### Scenario: mcp_error_unknown_method

- **WHEN** Claude calls an unknown MCP method
- **THEN** the server returns MCP error code `-32601`

#### Scenario: mcp_error_unparseable_json

- **WHEN** Claude sends unparseable JSON in the MCP request
- **THEN** the server returns MCP error code `-32700`

#### Scenario: parameter_validation_error

- **WHEN** Claude invokes a valid tool with invalid parameters (e.g., `git_log` with `limit=51`)
- **THEN** the error is returned via tool-level error handling (`{isError: true, reason: "..."}`), not as an MCP error code

---

### Requirement: Server registration

The server MUST be discoverable and launchable through two mechanisms: the `claude mcp add` command-line interface and a project `.mcp.json` configuration file. Both invocation methods MUST support the command signature: `python /abs/path/server.py --root /abs/path/to/repo`. Registration MUST fail clearly if the server script does not exist or is not executable; behavior is undefined for other edge cases (paths with spaces, conflicting registrations, malformed `.mcp.json`).

Trace: PRD-16

#### Scenario: registration_via_cli

- **WHEN** a user runs `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`
- **THEN** Claude Code registers the server and makes it available for invocation

#### Scenario: registration_via_config

- **WHEN** a project contains a `.mcp.json` file specifying the server with `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`
- **THEN** Claude Code registers the server when the project is opened

#### Scenario: registration_methods_recognized

- **WHEN** Claude Code starts or opens a project
- **THEN** it recognizes and loads both registration methods (CLI and config file)

#### Scenario: registration_server_not_found

- **WHEN** a user attempts to register a server using a nonexistent script path
- **THEN** the registration fails with a clear error message

#### Scenario: server_starts_with_root

- **WHEN** the registered server is invoked
- **THEN** it starts with the `--root` directory fixed at that path
