# DEVX-311 Interview

## Q1. Which CLIs should this MCP server expose?

The ticket says "Git and stuff, whatever the team uses." Help me be specific: Are we talking only about git, or should this include npm, docker, terraform, or other tools your team uses daily? What's the initial scope?

A: `git` and `rg` (ripgrep). Nothing else.

## Q2. What does "it can run git etc" mean in practice?

Should Claude be able to run *all* git commands, or only a safe subset (e.g., `git log`, `git status`, `git diff` but not `git push` or `git reset --hard`)? What's the boundary between "useful" and "dangerous"?

A: Only a specific, read-only subset. Claude can run four tools total: `git_status`, `git_log` (with limit 1–50, default 10), `git_diff_stat`, and `rg_search`. No write operations like push, commit, or checkout are exposed.

## Q3. Which Claude products need this?

"Needs to work with Claude Code" — does that mean the Claude Code CLI, the web app at claude.ai/code, IDE extensions, or all of them? Or do you mean something else by "Claude Code"?

A: No decision - treat it as a non-goal.

## Q4. What does "nothing dangerous" mean for your threat model?

The comment hints you had a bad experience with an overly-permissive shell command server. What specifically went wrong, and what are you protecting against now? (Repo corruption? Credentials leak? Accidental destructive commands?)

A: The specific incident isn't documented here. The concrete protections are: commands run as argument lists without a shell, only the four read-only operations above are available, each command has a 10-second timeout, output is limited to 8000 characters, and arguments are handled carefully to prevent flag injection (that is why `rg` uses `-e` and `--`).

## Q5. How should the server handle commands that could be risky?

If Claude (or the user) tries to run a potentially dangerous command like `git reset --hard` or `git push --force`, should the server block it, warn the user, require confirmation, or something else?

A: Only the four specified tools are available. If Claude or a user tries to run anything else, the server returns a JSON-RPC error code -32602 (unknown tool name).

## Q6. What counts as "tools show up in Claude" for acceptance testing?

The acceptance criteria say "tools show up in Claude." How do we verify this works? Should there be an integration test with Claude Code, a screenshot, or are we just checking that the MCP server registers the tools correctly?

A: No decision - treat it as a non-goal.

## Q7. How should errors be reported back to Claude?

When a command times out (10 seconds), hits the output limit (8000 chars), or fails, what should the server return? Plain text error message, or a specific JSON structure? Does Claude need to distinguish between "command failed" vs. "output was truncated"?

A: A tool that fails returns a normal result with `isError: true` and the reason as text, so the model can read it and adapt.

## Q8. What parameters are exposed for `git_log` and `rg_search`?

For `git_log`: are flags like `--oneline`, `--all`, `--format` allowed, or is it just the commit count limit? For `rg_search`: what's the full signature — how does Claude specify the search pattern, the directory, and the flags like `-i` (case-insensitive)?

A: For `git_log`, the command is `git log --oneline -n <limit>`, with a single argument `limit` (integer 1–50, default 10). For `rg_search`, the command is `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`, with arguments `pattern` (required non-empty string) and `path` (optional, default `.`).

## Q9. How should the server handle git repositories in unusual states?

Should the server work if the repo is in the middle of a merge, rebase, or cherry-pick? Should it error, or just return what it can (e.g., `git_status` shows the conflict state)?

A: No decision - treat it as a non-goal.

## Q10. Is there documentation or a test suite that defines the expected behavior?

Should this task include writing an MCP schema, unit tests, integration tests, or all three? Who validates that it meets the acceptance criteria?

A: No decision - treat it as a non-goal.

## Q11. What are the parameters and behavior for `git_diff_stat`?

Is it just `git diff --stat` with an optional ref argument, like a commit hash?

A: `git_diff_stat` accepts no arguments — it runs `git diff --stat` exactly as listed. No optional ref argument is specified.

## Q12. When output hits the 8000-character limit mid-stream, what happens?

Should the server return a partial result with `isError: true`, or truncate silently and return what fits?

A: Output truncation is silent, not an error. The specification says output is "cut at **8000 characters** with a `[truncated]` marker." It does not return `isError: true`.

## Q13. What should the tool descriptions say in the MCP schema?

For example, should `rg_search` say "Search repository files" or something more specific?

A: No decision — treat it as a non-goal.

## Q14. Where should this MCP server run, and how does Claude discover it?

Where should this MCP server run — as a standalone process, embedded in Claude Code, or something else? How does Claude discover it?

A: No decision — treat it as a non-goal. The specification covers activation via `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo` or a `.mcp.json` file, but does not specify server deployment location or Claude's discovery mechanism beyond this.

## Q15. Does `git_status` output have any specific format?

Does `git_status` output the raw result of `git status`, or is it formatted/structured in any way?

A: No decision - treat it as a non-goal.

## Q16. If the `--root` path is not a git repository, what should happen?

If the `--root` path passed to the server is not a git repository, what should the server do? Return an error on any git tool invocation, or silently return empty/blank results?

A: No decision - treat it as a non-goal.

## Q17. How should ripgrep exit status 1 (no matches found) be handled?

When `rg_search` finds no matches, ripgrep exits with status code 1. Should this be treated as a success (returning an empty result), or as an error?

A:

## Q18. How does the `--root` parameter define the working context?

When the server is invoked with `--root /abs/path/to/repo`, are all tool invocations (git commands, rg search paths) executed relative to this directory? Is this the current working directory for spawned processes?

A:

## Q19. Should the server reject paths that escape the root directory?

For `rg_search`, if Claude provides a path argument like `../../../etc/passwd`, should the server reject it as a path traversal attempt, or allow it?

A:

## Q20. Which JSON-RPC error codes should the server specify?

Besides -32602 for unknown tool name, should the PRD specify error codes for JSON-RPC parse errors, invalid parameters, or other standard MCP errors?

A:

## Q21. Should ripgrep exit status 1 (no matches) be treated as success?

When `rg_search` finds no matches, ripgrep returns exit status 1. Should this be treated as a successful result (empty matches), or as an error?

A: Yes. `rg` exiting 1 means "no matches"; that is a successful result, not an error.

## Q22. What is the operational role of the `--root` directory?

When the server is invoked with `--root /abs/path/to/repo`, what is the relationship between this path and tool execution? Are all commands run with this as the current working directory? Is it a constraint on what paths can be accessed?

A: The `--root` directory is fixed at startup. It serves as a constraint on what paths can be accessed by the tools — a `path` that resolves outside the root is rejected with a tool error saying the path escapes the root.

## Q23. Should the server reject paths outside the root directory?

For `rg_search`, if Claude provides a `path` argument like `../../../etc/passwd`, should the server reject paths that escape the root (path traversal protection), or allow them?

A: Yes. The server must reject paths outside the root directory with a tool error saying the path escapes the root.

## Q24. What stdio transport and MCP protocol version should be used?

The judge asks: what is the stdio transport mechanism (how do tools communicate input/output)? And which MCP protocol version should the server implement?

A: MCP over **stdio**: newline-delimited JSON-RPC 2.0, protocol version **`2025-06-18`**.

## Q25. What error code should be returned for JSON-RPC parse errors?

When the MCP client sends malformed JSON-RPC, what error code should the server return (in addition to -32602 for unknown methods)?

A: **-32700** for unparseable JSON.

## Q26. How should the server be registered with Claude Code?

How does a user set up this MCP server to work with Claude Code? (Q14 mentioned `claude mcp add` and `.mcp.json` but didn't fully specify the registration process.)

A: Either of two methods must work: `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`, or a project `.mcp.json` with the same command.

## Q27. What JSON-RPC error code should the server return for an unknown JSON-RPC method name?

When the MCP client sends a JSON-RPC request with a method name that is not a recognized MCP method (different from an unknown tool name within a valid method), what error code should the server return?

A:

