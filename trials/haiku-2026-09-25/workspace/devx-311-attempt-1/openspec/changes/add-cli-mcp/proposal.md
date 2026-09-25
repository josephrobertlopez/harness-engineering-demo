# Add CLI MCP Server for Git and Ripgrep (DEVX-311)

## Why

Claude needs safe, read-only access to repository inspection tools (git, ripgrep) via MCP so it can understand and analyze code in repositories. The platform previously attempted an overly-permissive shell command MCP server that created security risks; this design provides useful repository tools while preventing injection attacks, command abuse, and escape from the designated repository root.

## What Changes

- Add MCP server capability `cli-mcp` that exposes four read-only tools: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`
- Tools execute with no shell interpretation; all arguments are passed as argument arrays, preventing shell injection
- Implement safety constraints: 10-second timeout per invocation, 8000-character output limit with truncation, path validation to prevent escape from root directory
- Support MCP over stdio with newline-delimited JSON-RPC 2.0 protocol (version `2025-06-18`)
- Provide two registration methods: `claude mcp add cli-tools` CLI command and `.mcp.json` project configuration file

## Capabilities

### New Capabilities

- `cli-mcp`: MCP server providing safe, read-only access to `git` and `rg` (ripgrep) commands within a designated repository root
  - Tools: `git_status`, `git_log` (with limit 1–50, default 10), `git_diff_stat`, `rg_search` (pattern + optional path)
  - Isolation: All execution occurs within the `--root` directory; paths escaping root are rejected
  - Safety: No shell interpretation, 10-second timeout, 8000-character output limit, argument injection prevention

## Impact

- **For Claude**: Gains ability to inspect repository state, commit history, and search code for analysis and understanding
- **For users**: Can set up repository tools in Claude Code via CLI (`claude mcp add cli-tools -- python /path/server.py --root /path/to/repo`) or project config (`.mcp.json`)
- **For security**: Eliminates the overly-permissive shell command server pattern; all operations are constrained to a specific repo and bounded by timeout/output limits
- **For implementation**: Requires an MCP server implementation (~400-600 lines of code, including command execution, path validation, error handling, protocol marshaling)
