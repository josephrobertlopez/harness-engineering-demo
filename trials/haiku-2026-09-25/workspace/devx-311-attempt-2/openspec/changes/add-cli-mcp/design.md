# Design — add-cli-mcp

## Technical Approach

The implementation is a standalone MCP server that:

1. **Launches as a subprocess** managed by Claude Code via the MCP protocol over stdio
2. **Accepts `--root` argument** to define the directory boundary for all operations
3. **Exposes four tools** via MCP with strict argument validation
4. **Runs commands as argument arrays** (never through a shell) to prevent injection
5. **Enforces constraints** (10s timeout, 8000-char limit, read-only, no path escaping)
6. **Returns results** with `isError: true/false` for tool-level errors and standard MCP error codes for protocol errors

## Architecture Decisions

### Decision: Argument List vs Shell Execution
**Reason**: Eliminates shell injection and metacharacter interpretation. Commands are invoked directly as arrays (e.g., `["git", "status", ...]`), not parsed by a shell.

### Decision: Separate Tool-Level and Protocol-Level Errors
**Reason**: Tool invocation errors (bad arguments, missing binary, timeout) return `{isError: true, reason: "..."}` in the tool result. MCP protocol errors (unknown tool, malformed JSON) return standard error codes (-32602, -32601, -32700). This distinction is clearer for client error handling.

### Decision: Fixed Root Directory at Startup
**Reason**: Simplifies path validation and prevents directory traversal attacks. All paths are validated relative to `--root`, and escapes are rejected.

### Decision: Four Tools, Not Arbitrary Git/Ripgrep
**Reason**: Reduces attack surface and enforces read-only semantics. Only `git status`, `git log`, `git diff` operations are exposed; ripgrep is limited to pattern and path arguments with fixed flags.

### Decision: Fixed Ripgrep Flags
**Reason**: Prevents flag injection and ensures output consistency. Flags like `-e`, `--`, `--line-number`, `--no-heading`, `--max-count 50` are hardcoded; Claude provides only pattern and path.

### Decision: 10-Second Timeout and 8000-Character Output Limit
**Reason**: Prevents resource exhaustion (CPU, memory, bandwidth). Large repositories or slow operations are truncated and timed out gracefully.

## File Changes

### New Files

```
server.py
├── MCP server implementation
├── Tool handlers: git_status, git_log, git_diff_stat, rg_search
├── Argument validation and path checking
├── Timeout/output limit enforcement
└── Error handling (isError pattern, MCP codes)

tests/
├── test_git_status.py
├── test_git_log.py
├── test_git_diff_stat.py
├── test_rg_search.py
├── test_error_handling.py
├── test_path_isolation.py
├── test_timeout_and_limits.py
└── test_registration.py
```

### Configuration

```
.mcp.json (example)
├── Defines server command and root directory
└── Read by Claude Code for auto-registration
```

## Implementation Phases

1. **Core MCP server** (handles MCP protocol, initialization, tool dispatch)
2. **Tool implementations** (git_status, git_log, git_diff_stat, rg_search)
3. **Security layer** (path validation, timeout, output limits, argument validation)
4. **Testing** (unit tests for each tool, integration tests, isolation tests)
5. **Documentation** (README, installation, configuration)

## Testing Strategy

- Unit tests per tool with valid and invalid inputs
- Boundary tests for limits (limit=1, limit=50 for git_log; path=., path=../, etc.)
- Error cases (missing binary, non-existent git repo, timeout)
- Security tests (symlink escape attempts, path traversal, flag injection)
- Integration tests (full MCP handshake, tool invocation, error responses)
