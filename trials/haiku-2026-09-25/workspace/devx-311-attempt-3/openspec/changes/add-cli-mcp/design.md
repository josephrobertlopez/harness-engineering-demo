# Design: CLI Access MCP Server

## Technical Approach

Build a standalone Python MCP server that:
1. Accepts a `--root` flag specifying the working directory
2. Exposes four tools via MCP protocol over stdio
3. Invokes git and ripgrep as subprocesses with argument lists (no shell)
4. Validates all paths remain within the configured root
5. Enforces 10-second timeout and 8000-character output truncation
6. Returns structured error responses with `isError: true`

## Architecture Decisions

### Decision: Separate Tools Instead of Generic Command

**Reason:** The product owner explicitly rejected a "run any shell command" MCP after a previous bad experience. By exposing only four specific tools (git_status, git_log, git_diff_stat, rg_search), we prevent command injection and scope creep.

### Decision: Path Validation at Tool Boundary

**Reason:** `rg_search` must validate that the `path` argument resolves within `--root` before invoking ripgrep. This prevents users from escaping the sandbox.

### Decision: Special Case for `rg` Exit Code 1

**Reason:** ripgrep uses exit code 1 to mean "no matches found" (not an error). We treat this as a successful result to allow Claude to distinguish between "no matches" and "command failed."

### Decision: MCP Protocol v2025-06-18 over stdio

**Reason:** Matches Claude Code's MCP server discovery and configuration mechanism. stdio transport is simple and works across web, CLI, and IDE environments.

## File Changes

- `cli_tools_mcp/server.py` — Main MCP server implementing initialize, ping, tools/list, tools/call
- `cli_tools_mcp/tools.py` — Tool implementations (git_status, git_log, git_diff_stat, rg_search)
- `cli_tools_mcp/sandbox.py` — Path validation and command timeout logic
- `tests/test_tools.py` — Unit tests for each tool and scenario
- `README.md` — Installation and usage instructions
