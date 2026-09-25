# PRD — Give Claude our CLIs through MCP (DEVX-311)

## Problem

Claude Code users need programmatic access to repository information and search capabilities. Currently, Claude cannot invoke git commands or search tools to inspect repositories, limiting its ability to understand and work with code.

## Users

Claude Code users who develop in repositories and need Claude to inspect git history, status, or search code.

## Requirements

### PRD-1: Available tools

The MCP server SHALL expose exactly four tools to Claude via the MCP protocol, named in snake_case: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`. These tools wrap two underlying CLIs: `git` (restricted to three read-only operations) and `rg` (ripgrep, restricted to pattern search). No other CLIs, shell commands, or general-purpose tool invocation SHALL be available.

- WHEN Claude invokes the MCP server THEN only these four named tools are available
- WHEN Claude attempts to invoke any other tool, shell command, or any CLI not in the whitelist (git, rg) THEN it receives an error

Source: interview.md Q1, Q10, Q15

### PRD-2: No shell execution

Commands MUST run as argument lists with no shell invocation ever. This prevents shell metacharacters, environment variable expansion, and command chaining.

- WHEN Claude provides arguments to any tool THEN they are passed as an argument list, never through a shell
- WHEN Claude provides shell metacharacters (e.g., `|`, `>`, `;`) THEN they are treated as literal strings

Source: interview.md Q2

### PRD-3: Read-only operations

All operations MUST be read-only. Write operations MUST be forbidden, and git operations MUST not modify the repository.

- WHEN Claude invokes any tool THEN no files are created, modified, or deleted
- WHEN Claude attempts a write operation through git THEN the operation fails with an error

Source: interview.md Q2, Q7

### PRD-4: Timeout enforcement

Each underlying command execution (git or rg process) MUST have a maximum execution time of 10 seconds. Invocations exceeding this limit MUST be forcibly terminated and reported as errors. Whether partial output is captured before termination is not specified (see Non-goals).

- WHEN a git or rg command runs longer than 10 seconds THEN the process is forcibly terminated
- WHEN a command times out after 10 seconds THEN the result includes `isError: true` and a reason string containing "timeout" or similar indication

Source: interview.md Q2, Q3, Q16

### PRD-5: Output truncation

Output from any tool MUST be truncated at 8000 characters (counted as Unicode characters, not bytes). If truncation occurs, the output MUST end with the marker `[truncated]`.

- WHEN a command produces more than 8000 characters of output THEN output is cut at 8000 Unicode characters
- WHEN output is exactly 8000 characters or less THEN output is not truncated
- WHEN output exceeds 8000 characters THEN the result ends with the literal string `[truncated]`
- WHEN output is truncated THEN the 8000-character limit is enforced before appending `[truncated]`

Source: interview.md Q2, Q3

### PRD-6: Root directory isolation

The server MUST run within a root directory fixed at startup via the `--root` flag. All path arguments MUST be validated to ensure they do not escape this root. Paths that would escape the root MUST be rejected with an error.

- WHEN Claude provides a path argument THEN it is validated to stay within the root directory
- WHEN a path would escape the root (e.g., via `../` traversal) THEN the command fails with `isError: true` and a reason string

Source: interview.md Q7

### PRD-7: git_status operation

The `git_status` tool MUST accept no arguments and MUST invoke `git status --porcelain=v1 --branch`. It returns the short-form status of the working directory.

- WHEN Claude invokes `git_status` with no arguments THEN it runs `git status --porcelain=v1 --branch` and returns the result
- WHEN Claude provides any arguments to `git_status` THEN the operation fails with `isError: true`

Source: interview.md Q13

### PRD-8: git_log operation

The `git_log` tool MUST accept one optional argument, `limit`, which MUST be an integer from 1 to 50 with a default of 10. It MUST invoke `git log --oneline -n <limit>`. Any non-integer or out-of-range value MUST be rejected with an error.

- WHEN Claude invokes `git_log` without arguments THEN it runs `git log --oneline -n 10`
- WHEN Claude invokes `git_log` with `limit=1` THEN it runs `git log --oneline -n 1`
- WHEN Claude invokes `git_log` with `limit=50` THEN it runs `git log --oneline -n 50`
- WHEN Claude invokes `git_log` with `limit=5` THEN it runs `git log --oneline -n 5`
- WHEN Claude provides a `limit` of 0 or less THEN the operation fails with `isError: true` and a reason indicating the limit must be at least 1
- WHEN Claude provides a `limit` greater than 50 THEN the operation fails with `isError: true` and a reason indicating the limit must not exceed 50
- WHEN Claude provides a non-integer `limit` (e.g., string, float, null) THEN the operation fails with `isError: true` and a reason indicating limit must be an integer

Source: interview.md Q13

### PRD-9: git_diff_stat operation

The `git_diff_stat` tool MUST accept no arguments and MUST invoke `git diff --stat`. It returns a summary of changes in the working directory.

- WHEN Claude invokes `git_diff_stat` with no arguments THEN it runs `git diff --stat` and returns the result
- WHEN Claude provides any arguments to `git_diff_stat` THEN the operation fails with `isError: true`

Source: interview.md Q13

### PRD-10: rg_search operation

The `rg_search` tool MUST accept a pattern argument (required) and a path argument (optional, defaults to `.`). The server MUST invoke ripgrep with the exact flag sequence: `rg -e <pattern> -- <path>`, where the pattern is passed after `-e` and before `--`. All other ripgrep flags (`--line-number`, `--no-heading`, `--color never`, `--max-count 50`) are fixed by the implementation and not exposed to Claude. Any argument not in the pattern or path parameters MUST be rejected. This command structure prevents flag injection: patterns beginning with `-` are treated as literal search strings because they are passed after `-e` and before `--`.

- WHEN Claude invokes `rg_search` with pattern `foo` THEN the server runs `rg --line-number --no-heading --color never --max-count 50 -e foo -- .` from the root directory
- WHEN Claude invokes `rg_search` with pattern `foo` and path `src/` THEN the server runs `rg --line-number --no-heading --color never --max-count 50 -e foo -- src/`
- WHEN Claude provides a pattern beginning with `-` (e.g., pattern `-v`) THEN it is treated as a literal search string: `rg --line-number --no-heading --color never --max-count 50 -e -v -- .`
- WHEN Claude provides any other arguments or flags THEN the operation fails with `isError: true`

Source: interview.md Q1, Q11, Q14

### PRD-11: Default search path

When `rg_search` is invoked without a path argument, it MUST default to `.`. Since all commands execute in the root directory specified by `--root`, the default `.` means the search starts from that root directory.

- WHEN Claude invokes `rg_search` with only a pattern THEN the search scans files starting from the root directory

Source: interview.md Q14

### PRD-12: Tool-level error handling

Any tool invocation that fails—due to bad arguments, path escaping attempts, missing binary, non-zero exit code, or timeout—MUST return a result with `isError: true` and a reason string in plain text. Tool-level errors are distinct from MCP protocol-level errors (see PRD-15). Exception: `rg` exit code 1 (no matches found) MUST be treated as a successful result, not an error.

- WHEN a tool is invoked and the underlying command fails (bad arguments, missing binary, non-zero exit, timeout) THEN the result is `{isError: true, reason: "<error reason>"}`
- WHEN `rg_search` completes with no matches (exit code 1) THEN the result is `{isError: false}` with empty or minimal output
- WHEN a path argument escapes the root directory THEN the result is `{isError: true, reason: "<reason indicating path outside root>"}`

Source: interview.md Q8

### PRD-13: Platform integration

The MCP server MUST operate over stdio and be compatible with Claude Code. It SHALL work with Claude Code's MCP integration via standard input/output.

- WHEN Claude Code starts the MCP server THEN it communicates via stdio
- WHEN Claude Code invokes a tool THEN the MCP protocol is used over stdio

Source: interview.md Q4

### PRD-14: MCP protocol version

The server MUST implement and advertise MCP protocol version `2025-06-18` in the MCP initialize response.

- WHEN Claude Code initiates an MCP initialize handshake THEN the server responds with protocol version `2025-06-18`
- WHEN the server starts THEN it is compatible with MCP protocol version `2025-06-18`

Source: interview.md Q17

### PRD-15: MCP protocol-level error codes

The server MUST return MCP-standard error codes for protocol-level failures that occur before tool invocation. These are distinct from tool-level errors (see PRD-12). The server MUST return: `-32602` for unknown tool name, `-32601` for unknown method, and `-32700` for unparseable JSON. Tool-level errors (bad arguments, missing binary, path escape attempts, command timeout) use the PRD-12 mechanism (`isError: true` in tool result) instead.

- WHEN Claude invokes an MCP call for a tool that does not exist (e.g., `nonexistent_tool`) THEN the server returns MCP error code `-32602`
- WHEN Claude calls an unknown MCP method THEN the server returns MCP error code `-32601`
- WHEN Claude sends unparseable JSON in the MCP request THEN the server returns MCP error code `-32700`
- WHEN Claude invokes a valid tool with invalid parameters (e.g., `git_log` with `limit=51`) THEN the error is returned via PRD-12 mechanism (`{isError: true, reason: "..."}`), not as an MCP error code

Source: interview.md Q18

### PRD-16: Server registration

The server MUST be discoverable and launchable through two mechanisms: the `claude mcp add` command-line interface and a project `.mcp.json` configuration file. Both invocation methods MUST support the command signature: `python /abs/path/server.py --root /abs/path/to/repo`. Registration MUST fail clearly if the server script does not exist or is not executable; behavior is undefined for other edge cases (paths with spaces, conflicting registrations, malformed `.mcp.json`).

- WHEN a user runs `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo` THEN Claude Code registers the server and makes it available for invocation
- WHEN a project contains a `.mcp.json` file specifying the server with `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo` THEN Claude Code registers the server when the project is opened
- WHEN Claude Code starts or opens a project THEN it recognizes and loads both registration methods
- WHEN a user attempts to register a server using a nonexistent script path THEN the registration fails with a clear error message

Source: interview.md Q19

## Non-goals

- Performance optimization targets (not decided)
- Server installation and who can install it (not decided)
- Environment variable exposure and secret handling (not decided)
- Support for Claude.ai, other IDE plugins, or other platforms (no decision; Claude Code only)
- Public distribution vs. internal-only scope (not decided)
- Result metadata including stderr, exit codes, or execution time (not decided)
- Partial results when commands timeout (not decided)
- Complete JSON schema structure for error responses (not decided)
- Server startup validation: whether server validates the `--root` directory exists and is a git repo at startup, or defers validation to tool invocation (not decided)
- Path validation approach: whether symlink resolution is used or string-based checks for path isolation (not decided)
- Null and empty argument handling for `rg_search` pattern argument (not decided)
- MCP argument passing format details beyond "argument list" (not decided)
- Error message format and specific examples for each error type (not decided)
- Timeout scope: whether 10-second limit includes MCP overhead, argument parsing, process spawning, or only command execution (not decided)
- Registration edge cases: paths with spaces, conflicting registrations, malformed `.mcp.json`, precedence between registration methods (not decided)

## Open questions

- "Who are the primary users?" → PRD-1, PRD-13
- "What is the exact threat model?" → PRD-2, PRD-3, PRD-6
- "How should large outputs be handled?" → PRD-5
- "What are the git operation signatures?" → PRD-7, PRD-8, PRD-9
- "What ripgrep options should Claude access?" → PRD-10, PRD-11
