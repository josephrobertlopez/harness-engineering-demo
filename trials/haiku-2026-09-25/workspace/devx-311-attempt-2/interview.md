# DEVX-311 Interview Record

### Q1. Which CLIs should this MCP server expose, and which are explicitly out of scope?
The ticket says "Git and stuff, whatever the team uses" — but that's unclear. Should we support all CLIs the user has installed, or a curated list? Does "the team" mean Anthropic's devx team, Claude Code users, or both? Are there CLIs that should be explicitly blocked (system commands, dangerous tools)?

A: Two: `git` and `rg` (ripgrep). Nothing else. Not a general shell.

### Q2. What is the specific threat model for "nothing dangerous"?
Previous attempts at "run any shell command" were rejected. What attacks or misuse are we preventing? Are we worried about: privilege escalation, unauthorized data access, resource exhaustion (CPU/disk/memory), or exfiltration of secrets from .env files?

A: Commands run as an argument list with no shell, ever. Only the two specified tools are available; no write operations. Each command gets a 10 second timeout. Output is cut at 8000 characters with a `[truncated]` marker. Patterns starting with `-` are searched literally (protected by `-e` and `--`), preventing flag injection.

### Q3. How should Claude handle long-running commands, large outputs, or commands that hang?
When Claude runs `git clone` on a large repo, or a command returns gigabytes of output, what's the expected behavior? Should there be timeouts, output size limits, or progress streaming?

A: 10 second timeout per command. 8000 character output limit with `[truncated]` marker.

### Q4. What is the acceptance criterion "tools show up in Claude" — is this about Claude.ai, Claude Code CLI, Claude Code IDE plugins, or all three?
Should the server work identically across all Claude products, or are there platform-specific differences?

A: MCP over stdio works with Claude Code. No decision on web, other IDE plugins, or other platforms—treat as non-goals.

### Q5. Who are the users of this server, and what are their primary workflows?
Are we building this for Claude Code users developing open-source repos, Anthropic employees, or internal tooling? That changes what CLIs matter and what "safe" means.

A:

### Q6. What are the performance targets for command execution?

A: No decision—treat as a non-goal.

### Q7. What are the security boundaries around the server installation and environment variable access?

A: The server runs in a root directory fixed at startup with `--root`; paths escaping it are rejected. Commands are read-only. Who can install and what environment secrets are exposed: no decision—treat as non-goals.

### Q8. How should the server handle errors when a command fails—bad arguments, path escape attempts, missing binary, non-zero exit, or timeout?

A: A tool that fails—bad argument, path outside root, missing binary, non-zero exit, or timeout—returns a normal result with `isError: true` and reason as text. Exception: `rg` exit code 1 (no matches) is a successful result, not an error.

### Q9. What protection exists against shell injection or flag injection through pattern arguments?

A: No shell execution ever. Pattern arguments are protected by `-e` and `--`, preventing them from being parsed as flags.

### Q10. What is the tool schema for `git` — should Claude have access to all git subcommands, or a curated whitelist?

A: Claude does not have access to all `git` subcommands. Instead, Claude has a curated whitelist of exactly three git operations: `git_status`, `git_log`, and `git_diff_stat`.

### Q11. What flags and options should `rg` expose to Claude — all ripgrep flags, or a restricted set?

A: `rg` does not expose all ripgrep flags to Claude. Claude sees a restricted set: the pattern argument and the optional path argument only. All other flags (`--line-number`, `--no-heading`, `--color never`, `--max-count 50`, `-e`, and `--`) are fixed by the implementation. Any argument not listed is rejected.

### Q12. What fields should the MCP tool result include — just `stdout` and `isError`, or also `stderr`, `exitCode`, and other metadata?

A: No decision—treat as a non-goal.

### Q13. What is the exact signature of each git operation—what arguments does `git_status` accept, what does `git_log` accept (e.g. commit count limit, file paths), and what does `git_diff_stat` show (working directory changes or a specific commit)?

A: `git_status` accepts no arguments and runs `git status --porcelain=v1 --branch`. `git_log` accepts one argument, `limit`, an integer from 1–50 with default 10, and runs `git log --oneline -n <limit>`. `git_diff_stat` accepts no arguments and runs `git diff --stat`, which shows working directory changes.

### Q14. When Claude calls `rg` without a path argument, should it search from the root directory specified by `--root`, or from the current working directory?

A: When Claude calls `rg` without a path argument, it defaults to `.`. Since all commands run in the root directory fixed at startup with `--root`, the default `.` means it searches from that root directory.

### Q15. Should the MCP tools be named with snake_case (`git_status`, `git_log`, `git_diff_stat`) or another naming convention?

A: The tools are named with snake_case: `git_status`, `git_log`, `git_diff_stat`, and `rg_search`.

### Q16. When a command times out at the 10-second limit, should the server return partial results (output gathered before timeout) or just an error with `isError: true`?

A: No decision—treat as a non-goal. The document states that a timeout returns a normal result with `isError: true` and the reason as text, but it does not specify whether partial output gathered before the timeout should be included in that result or omitted.

### Q17. Which version of the MCP protocol must this server implement?

A: The MCP protocol version is `2025-06-18`.

### Q18. What is the exact JSON schema for error responses, including responses for unknown tools, unknown methods, and parse errors?

A: No decision—treat as a non-goal. The document specifies error codes (unknown tool name → `-32602`, unknown method → `-32601`, unparseable JSON → `-32700`) and states that tool failures return a normal result with `isError: true` and the reason as text, but does not provide the complete JSON schema structure for these responses.

### Q19. How should Claude Code discover and launch this MCP server—via environment variable, configuration file, command-line flag, or another mechanism?

A: Two mechanisms: the `claude mcp add` command-line interface (`claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`), or a project `.mcp.json` configuration file with the same command. Either must work.

### Q20. When the server starts with `--root /path`, what should happen if that path doesn't exist, isn't readable, or isn't a git repository? Should the server fail to start, or start successfully and return errors at tool invocation time?

A:
