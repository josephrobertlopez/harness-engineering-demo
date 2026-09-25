# DEVX-311: Add CLI tools to Claude through MCP

## Why

Claude Code users cannot inspect git history, repository status, or search file contents without leaving the IDE and running commands manually. This blocks common development workflows. An MCP server exposing read-only git and ripgrep commands would let Claude execute these tools directly, making code exploration faster and more integrated.

**Related**: `prd.md`

## What Changes

- Add MCP server that exposes four CLI tools: `git_status`, `git_log`, `git_diff_stat`, `rg_search`
- Server communicates over stdio using JSON-RPC 2.0 (protocol version `2025-06-18`)
- Developers activate it via `claude mcp add cli-tools -- python /path/server.py --root /path/to/repo` or `.mcp.json`
- All commands run in a fixed root directory with path boundary enforcement
- Resource limits: 10-second timeout, 8000-character output truncation
- Security: no shell interpretation, no git write operations, patterns treated as literals

## Capabilities

### New Capabilities

- **Read-only CLI access**: Claude can invoke `git_status`, `git_log`, `git_diff_stat`, `rg_search`
- **MCP integration**: Server works with Claude Code IDE via stdio JSON-RPC
- **Path safety**: Commands confined to a root directory; path escapes rejected
- **Literal pattern matching**: Ripgrep patterns starting with `-` treated as search terms, not flags

## Impact

- **Scope**: CLI tools limited to git and ripgrep; no general shell
- **Security**: No write operations; no shell injection risk
- **Scale**: Output truncated at 8000 characters; commands timeout after 10 seconds
- **Users**: Claude Code IDE users; no impact on other tools or APIs
