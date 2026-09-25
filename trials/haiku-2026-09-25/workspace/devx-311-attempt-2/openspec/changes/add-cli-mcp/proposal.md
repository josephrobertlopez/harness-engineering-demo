# OpenSpec Proposal — add-cli-mcp

## Why

**Ticket**: DEVX-311

**Problem**: Claude Code users currently cannot programmatically access git and ripgrep (rg) tools to inspect repositories, limiting Claude's ability to understand code context and perform repository analysis.

**Solution**: Implement an MCP server that exposes a curated set of git operations (status, log, diff-stat) and ripgrep search with strict security constraints (no shell, read-only, timeouts, output limits). This enables Claude to safely look at repository state and search code without exposing dangerous capabilities.

**Alignment with PRD**: This change implements all 16 requirements from DEVX-311 PRD, with emphasis on security and controlled access.

---

## What Changes

- **New MCP server implementation** exposing four tools: `git_status`, `git_log`, `git_diff_stat`, `rg_search`
- **Security model**: No shell execution, read-only operations, 10-second timeout per command, 8000-character output limit, path validation, flag injection protection
- **MCP protocol compliance**: Protocol version `2025-06-18`, standard error codes, stdio communication
- **Server registration**: Support for `claude mcp add` CLI and `.mcp.json` configuration file
- **Root directory isolation**: Commands constrained to a user-specified root directory with path escape validation

---

## Capabilities

### New Capabilities

- **git_status**: Query working directory status (porcelain format with branch info)
- **git_log**: Retrieve commit log with configurable limit (1–50, default 10)
- **git_diff_stat**: Display summary of working directory changes
- **rg_search**: Search repository for patterns with optional path argument
- **Security isolation**: Path validation, read-only enforcement, timeout/output limits
- **MCP server registration**: Register via CLI and project configuration file

---

## Impact

- **Users**: Claude Code users who develop in git repositories
- **Implementation scope**: Single MCP server binary/script
- **Integration points**: Claude Code's MCP server management system
- **Risk level**: Medium (security-critical, requires rigorous testing of isolation)
- **Dependencies**: MCP protocol 2025-06-18, git, ripgrep binaries on user's system
- **Backward compatibility**: N/A (new feature)

---

## Non-goals (Deferred)

The following items are explicitly out of scope for this change:

- Performance optimization targets
- Server installation and permissions management
- Environment variable/secret handling
- Support for other Claude platforms (web, other IDEs)
- Complete JSON schema for error responses
- Server startup validation
- Path validation approach (symlink handling)
- Null/empty argument behavior
- Timeout overhead scope
- Registration edge cases
- MCP argument format details
- Error message format/examples

These are documented in the PRD as "not decided" and should be addressed in follow-up work if needed.
