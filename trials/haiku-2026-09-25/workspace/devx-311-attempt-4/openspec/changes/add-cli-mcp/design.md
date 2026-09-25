# Design: CLI tools MCP server

## Technical Approach

The MCP server is a Python subprocess that:

1. Reads JSON-RPC 2.0 requests from stdin (newline-delimited)
2. Parses requests to extract tool name and arguments
3. Constructs and executes the appropriate CLI command as an argument list (no shell)
4. Enforces resource limits: 10-second timeout, 8000-character output cap
5. Returns responses with tool results or error information

The server enforces a fixed root directory (specified at startup via `--root`). All file paths are resolved relative to this root and validated to prevent escapes.

## Architecture Decisions

### Decision: MCP over stdio instead of TCP or HTTP

**Reason**: Stdio integration is simpler for the Claude Code IDE to manage; no network setup, automatic cleanup when the process exits. MCP spec supports stdio as the primary transport.

### Decision: Fixed root directory at startup, not per-request

**Reason**: Simplifies security model and eliminates risk of path confusion during execution. One root per server instance.

### Decision: Whitelist of four tools, not dynamic commands

**Reason**: Prevents accidental exposure of dangerous commands. Each tool is explicitly implemented and tested.

### Decision: Ripgrep with `-e pattern -- path` invocation

**Reason**: Ensures patterns are treated as search terms (not options) even if they start with `-`. The `--` separator prevents path interpretation as an option.

### Decision: 8000-character output limit, not streaming

**Reason**: Simplifies the implementation and prevents runaway output from consuming system resources. Claude can infer that results were truncated and re-request with a more specific pattern.

## File Changes

### New files

- `server.py`: Main MCP server implementation
  - Parse CLI arguments (`--root`)
  - Implement `tools/list` and `tools/call` MCP methods
  - Execute `git_status`, `git_log`, `git_diff_stat`, `rg_search`
  - Enforce resource limits and path boundaries

- `tests/test_*.py`: Unit tests for each scenario
  - Mock the CLI tools to verify behavior
  - Test error cases, resource limits, parameter validation

### Configuration

- Activation via `claude mcp add cli-tools -- python /path/server.py --root /path/to/repo`
- Or add to project `.mcp.json`:
  ```json
  {
    "cli-tools": {
      "command": "python /path/server.py --root /path/to/repo"
    }
  }
  ```
