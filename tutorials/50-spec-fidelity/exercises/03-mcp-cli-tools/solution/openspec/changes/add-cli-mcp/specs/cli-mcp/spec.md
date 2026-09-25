## ADDED Requirements

### Requirement: MCP over stdio

The server SHALL speak MCP over stdio as newline-delimited JSON-RPC 2.0 with
protocol version `2025-06-18`, answering `initialize`, `ping`, `tools/list`
and `tools/call`, and MUST NOT respond to notifications.

Trace: PRD-1

#### Scenario: Initialize handshake

- **WHEN** a client sends `initialize`
- **THEN** the result has `protocolVersion` `2025-06-18` and a `tools` capability
- **AND** a following `notifications/initialized` produces no response

#### Scenario: Stdio round trip

- **WHEN** the server runs as a process and receives `initialize` and `tools/list` lines
- **THEN** it writes exactly two JSON response lines with matching ids

### Requirement: Fixed tool catalogue

`tools/list` SHALL return exactly `git_status`, `git_log`, `git_diff_stat`
and `rg_search`, each with an input schema that sets
`additionalProperties: false`. The server MUST NOT run any binary other than
`git` and `rg`.

Trace: PRD-2

#### Scenario: Exactly four tools

- **WHEN** a client lists tools
- **THEN** the names are exactly `git_diff_stat`, `git_log`, `git_status`, `rg_search`
- **AND** every command the tools build starts with `git` or `rg`

#### Scenario: Unlisted argument rejected

- **WHEN** `git_status` is called with `{"args": "--all"}`
- **THEN** the result has `isError: true` and no command runs

### Requirement: git tools

`git_status` SHALL run `git status --porcelain=v1 --branch`, `git_diff_stat`
SHALL run `git diff --stat`, and `git_log` SHALL run
`git log --oneline -n <limit>` with integer `limit` from 1 to 50, default 10.

Trace: PRD-3

#### Scenario: Porcelain status

- **WHEN** `git_status` is called
- **THEN** the command is exactly `git status --porcelain=v1 --branch` in the root

#### Scenario: Log limit defaults to 10

- **WHEN** `git_log` is called with no arguments
- **THEN** the command is `git log --oneline -n 10`

#### Scenario: Log limit out of range

- **WHEN** `git_log` is called with `limit` 51, 0, or `true`
- **THEN** the result has `isError: true` and no command runs

#### Scenario: Real git status

- **GIVEN** git is installed and the root is a git repository
- **WHEN** `git_status` is called with the real runner
- **THEN** the result is not an error and starts with `##`

### Requirement: rg search

`rg_search` SHALL run
`rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`
with a required non-empty `pattern` and `path` defaulting to `.`. Exit status 1
MUST be reported as a successful "no matches" result.

Trace: PRD-4

#### Scenario: Flag-like pattern searched literally

- **WHEN** `rg_search` is called with `pattern` `--files`
- **THEN** the command contains `-e --files --` so rg reads it as a pattern

#### Scenario: No matches is not an error

- **WHEN** rg exits with status 1 and no output
- **THEN** the result is not an error and its text is `no matches`

#### Scenario: Empty pattern rejected

- **WHEN** `rg_search` is called with `pattern` `""`
- **THEN** the result has `isError: true`

### Requirement: Root confinement

Every command SHALL run with the `--root` directory as its working directory,
and a `path` resolving outside that directory MUST be rejected with an
`isError` result before any command runs.

Trace: PRD-5

#### Scenario: Path escaping root rejected

- **WHEN** `rg_search` is called with `path` `../..` or an absolute path outside the root
- **THEN** the result has `isError: true` mentioning the root, and no command runs

### Requirement: Execution limits

Commands SHALL run as argument lists with no shell and a 10 second timeout,
with output cut to 8000 characters followed by `[truncated]`. A missing
binary, a timeout, or a non-zero exit (other than rg's 1) MUST produce an
`isError` result carrying the reason.

Trace: PRD-6

#### Scenario: Missing binary

- **WHEN** the binary for a tool is not installed
- **THEN** the result has `isError: true` and says it is not installed

#### Scenario: Timeout

- **WHEN** a command runs longer than the timeout
- **THEN** the result has `isError: true` and says it timed out

#### Scenario: Non-zero exit

- **WHEN** git exits with status 128 and a message on stderr
- **THEN** the result has `isError: true` and contains the stderr message

#### Scenario: Output truncated

- **WHEN** a command prints more than 8000 characters
- **THEN** the text is the first 8000 characters followed by `[truncated]`

### Requirement: Protocol errors

The server SHALL answer an unknown tool name with JSON-RPC error -32602, an
unknown method with -32601, and an unparseable line with -32700 and a null id.

Trace: PRD-7

#### Scenario: Unknown tool

- **WHEN** a client calls tool `rm_rf`
- **THEN** the response is an error with code -32602

#### Scenario: Unknown method

- **WHEN** a client calls method `resources/list`
- **THEN** the response is an error with code -32601

#### Scenario: Malformed JSON

- **WHEN** a client sends the line `{not json`
- **THEN** the response is an error with code -32700 and id null

### Requirement: Registration with Claude Code

The implementation SHALL ship a `.mcp.json` declaring server `cli-tools`
that runs `server.py` with `--root`, matching
`claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`.

Trace: PRD-8

#### Scenario: Project config is valid

- **WHEN** `.mcp.json` is parsed
- **THEN** `mcpServers.cli-tools` runs `python` with `server.py` and `--root` in its args
