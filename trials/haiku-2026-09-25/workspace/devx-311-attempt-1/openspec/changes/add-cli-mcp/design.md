# Design: CLI MCP Server

## Technical Approach

The MCP server is a stateless, single-threaded process that:

1. **Accepts**: Newline-delimited JSON-RPC 2.0 requests on stdin
2. **Validates**: Each tool invocation against a whitelist of four operations and path constraints
3. **Executes**: Subprocess commands with timeout and output truncation
4. **Returns**: Structured JSON-RPC responses with error handling

The server is initialized with a `--root` directory that constrains all tool operations to paths within that root.

## Architecture Decisions

### Decision: MCP over stdio (not HTTP, WebSocket, or IPC)
**Reason**: Simplicity and Claude Code integration. Standard MCP communication pattern; no network exposure.

### Decision: Four fixed tools, no parameterization
**Reason**: Security boundary. Limiting to specific command signatures (`git log --oneline -n <limit>`, `rg --line-number --no-heading ... -e <pattern> -- <path>`) eliminates arbitrary flag injection and command combinations.

### Decision: 10-second timeout and 8000-character output limit
**Reason**: Prevent resource exhaustion. Large repositories could produce unbounded output; timeouts prevent hanging. Output limit prevents Claude from receiving gigabytes of data per tool call.

### Decision: Path validation at the tool level, not via chroot
**Reason**: Portable and observable. Chroot requires elevated privileges and is Unix-specific. Path validation is portable and its behavior is testable.

### Decision: Silent output truncation (no isError for truncation)
**Reason**: Match user expectations. Truncation is not a failure; it's a normal result of output boundaries. Claude can observe `[truncated]` and adjust its queries.

### Decision: Ripgrep exit 1 (no matches) is success
**Reason**: Semantic correctness. ripgrep exit 1 means "no matches found," which is a valid search result, not an error. Avoids confusing Claude when searching for a pattern that doesn't exist.

## File Changes

| File | Purpose | Status |
|------|---------|--------|
| `server.py` | Main MCP server; request handling, tool dispatch, subprocess execution | To implement |
| `test_server.py` | Unit and integration tests; one test per scenario | To implement |
| `README.md` | Setup and usage documentation | To implement |
| `.mcp.json` (example) | Example project configuration file | To implement (template) |

## Implementation Notes

- **Language**: Python 3.10+
- **Dependencies**: MCP SDK (if available), subprocess (stdlib), json (stdlib), asyncio (stdlib)
- **Testing**: pytest with fixtures for subprocess mocking
- **Security**: Argument arrays prevent shell injection; path normalization prevents `..` traversal; subprocess runs without shell=True
