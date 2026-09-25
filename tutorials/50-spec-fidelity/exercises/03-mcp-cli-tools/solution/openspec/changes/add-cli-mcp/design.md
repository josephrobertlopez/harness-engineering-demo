# Design: MCP server for git and rg

## Technical Approach

One stdlib module. `Server.handle(message) -> response | None` is a pure
JSON-RPC dispatcher; `Server.serve(stdin, stdout)` is the newline-delimited
stdio loop around it. Command execution goes through an injectable
`runner`, so tests assert the exact argument vector without needing git or
rg installed.

## Architecture Decisions

### Decision: hand-rolled JSON-RPC instead of the MCP Python SDK

The SDK (`mcp`, `FastMCP`) is the normal choice and the exercise README
shows it. The reference solution uses the stdlib so this repository's
grading stays install-free. The wire format is small: four methods, three
error codes.

### Decision: each tool builds its own argv; nothing is concatenated

A tool is a function from validated arguments to a fixed argument list.
No string ever reaches a shell, and user input only ever appears after `-e`
or `--`, where neither git nor rg can read it as an option.

### Decision: tool failures are results, protocol failures are errors

The MCP spec separates the two. A model can read an `isError` result and
try a smaller `limit`; it never sees a JSON-RPC error, which the client
swallows. So only "you called something that does not exist" is a
protocol error.

## Data Flow

stdin line → JSON → `handle` → `tools/call` → validate args → resolve path
inside root → argv → runner (no shell, timeout) → interpret exit code →
truncate → `{"content": [{"type": "text", ...}], "isError": ...}` → stdout.

## File Changes

- `impl/server.py` (new)
- `impl/.mcp.json` (new)
- `impl/tests/test_server.py` (new)
