# Proposal: Give Claude CLI access through MCP

**Ticket:** DEVX-311  
**PRD:** [prd.md](../../prd.md)

## Why

Claude needs read-only access to repository inspection tools (git and ripgrep) through MCP so developers can ask Claude to analyze repositories without manually copying tool output or exposing Claude to arbitrary shell commands. Current workarounds introduce friction and security risks.

## What Changes

- Implement an MCP server exposing four read-only tools: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`
- Restrict all commands to whitelisted parameters (no flags except those explicitly allowed)
- Enforce 10-second timeout per command; truncate output at 8000 characters
- Support deployment via `claude mcp add` or `.mcp.json` configuration
- Communicate using MCP protocol version `2025-06-18` over stdio
- Return detailed errors with `isError: true` flag and text explanation

## New Capabilities

- **Read-only git inspection:** Developers can ask Claude to view repository status, history, and diffs without shell access
- **Repository search:** Developers can ask Claude to search files using ripgrep patterns with path confinement to the configured root directory
- **Safe MCP server:** All commands run without shell invocation; no write operations allowed; strict parameter whitelisting

## Impact

- Developers gain seamless CLI access within Claude Code without security risks
- Implementation effort: 3 story points (medium priority task)
- No bundling required; users self-configure via `claude mcp add` or `.mcp.json`
