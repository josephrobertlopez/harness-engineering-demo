# DEVX-311 Interview

## Success Criteria

### Q1. Which CLIs should be exposed through this MCP server?
A: Two: `git` and `rg` (ripgrep). Nothing else. Not a general shell.

### Q2. What does "it can run git etc" mean — all git subcommands, or a specific whitelist?
A: Not all git subcommands. The server exposes a specific whitelist of four tools: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`.

### Q3. How do we verify success — do you need metrics (e.g., "Claude can execute git commands successfully N% of the time"), or is demonstrating that tools appear in Claude Code sufficient?
A: No decision - treat it as a non-goal.

## Constraints

### Q4. You said "we are not doing that again" after the shell command incident — what specific behaviors or attack vectors are we preventing?
A: Commands run as an argument list; no shell, ever. Only the four commands above; no write operations (commit, checkout, push). A pattern starting with `-` must be searched for, not parsed as a flag. Each command gets a **10 second** timeout. Output is cut at **8000 characters** with a `[truncated]` marker.

### Q5. Does this MCP server need to authenticate or authorize Claude's commands in any way, or does it trust whatever Claude Code sends it?
A: Q7 states that authentication is out of scope. Regarding whether the server needs to authorize or validate requests, no decision - treat it as a non-goal.

## Integration

### Q6. How should Claude Code discover and invoke this MCP server — as a stdio subprocess, SSE endpoint, or another mechanism?
A: MCP over **stdio**: newline-delimited JSON-RPC 2.0, protocol version **`2025-06-18`**. The developer activates it with `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`, or by adding the same command to a project `.mcp.json`.

## Error Handling

### Q7. When a command fails (timeout, permission denied, nonzero exit), what error information should the MCP server return to Claude?
A: A tool that fails—bad argument, path outside the root, missing binary, non-zero exit, or timeout—returns a normal result with **`isError: true`** and the reason as text. Unknown tool names get JSON-RPC error **-32602**; unknown methods get **-32601**; unparseable JSON gets **-32700**. Exception: `rg` exiting 1 (no matches) is a successful result, not an error.

## Tool Specifications

### Q8. What arguments and flags does each of the four tools accept — for example, does `git_log` accept `--oneline`, and what are the valid parameters for `rg_search`?
A: The four tools accept these arguments:

| tool | arguments |
|---|---|
| `git_status` | none |
| `git_log` | `limit`: integer 1–50, default 10 |
| `git_diff_stat` | none |
| `rg_search` | `pattern`: required non-empty string; `path`: optional, default `.` |

### Q9. When output is truncated at 8000 characters, should the `[truncated]` marker appear inline at the cut point, or separately in an error field?
A: No decision - treat it as a non-goal.

## Execution Context

### Q10. What is the working directory context for command execution — should commands run in the repository Claude Code is currently editing, or somewhere else?
A: Commands run in one root directory fixed at startup with `--root`. A `path` that resolves outside the root (`../`, an absolute path elsewhere) is rejected with a tool error saying the path escapes the root.

### Q11. What output format should the four tools return on success — plain text, JSON with structured fields, or something else? (For example, should `git_log` return raw git output, or a JSON array of commits with fields like hash, author, message?)
A: No decision - treat it as a non-goal.

### Q12. What should happen when an argument violates its constraints — for example, if `git_log` is called with `limit=0` or `limit=51`, or `rg_search` is called with an empty `pattern` string?
A: No decision - treat it as a non-goal.

### Q13. When output is truncated at 8000 characters, should the truncation respect UTF-8 character boundaries (to avoid splitting multibyte sequences), or is a hard byte cut acceptable?
A: No decision - treat it as a non-goal.

### Q14. For `rg_search`, when a `path` argument is provided, can it be a file (search in one file), a directory (search recursively), or both? What should happen if the path doesn't exist?
A: No decision - treat it as a non-goal.

### Q15. Should the MCP server process multiple concurrent tool calls from Claude in parallel, or serialize them?
A: No decision - treat it as a non-goal.

## Ripgrep Invocation

### Q16. When `rg_search` passes a pattern to ripgrep, how should it handle patterns starting with `-` to ensure they are searched as literals rather than parsed as flags?
A: The pattern is passed with the `-e` flag followed by `--` before the path. The exact command line is: `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`. The `-e` flag tells ripgrep the argument is a pattern, and the `--` signals that everything after it is a path, not an option. This ensures patterns starting with `-` are searched as literals, not parsed as flags.
