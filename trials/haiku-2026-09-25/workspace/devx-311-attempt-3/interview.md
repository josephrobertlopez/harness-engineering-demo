# DEVX-311 Interview

## Q1. Which CLIs should the MCP server expose?
A: Two: **`git`** and **`rg`** (ripgrep). Nothing else. Not a general shell.

## Q2. What does "safe" mean in this context—are we sandboxing execution, whitelisting specific commands, restricting file access, or something else?
A: "Safe" means: commands run as an argument list with no shell invocation ever; only the four read-only tools listed (git_status, git_log, git_diff_stat, rg_search); no write operations like commit, checkout, or push; patterns starting with `-` are searched, not parsed as flags; each command has a **10 second** timeout; output is truncated at **8000 characters** with a `[truncated]` marker if it exceeds that.

   **rg command invocation**: `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>`

## Q3. How do we measure success—is it "Claude can invoke tools without errors," or do we have specific use cases in mind like "Claude should be able to grep a repo" or "Claude should be able to review git diffs"?
A: No decision - treat it as a non-goal.

## Q4. Should this work across all Claude Code environments (web app, CLI, IDE extensions), or is there a specific primary target?
A: No decision - treat it as a non-goal.

## Q5. What happens when a command fails or times out—should Claude see stderr, and how should we handle long-running processes?
A: When a command fails—bad argument, path outside the root, missing binary, non-zero exit, or timeout—Claude sees a normal result with **`isError: true`** and the reason as text, so it can read the error and adapt. Exception: `rg` exiting with code 1 means "no matches," which is a successful result, not an error. Timeouts are **10 seconds** per command.

   **MCP protocol details**:
   - Transport: MCP over **stdio**
   - Protocol version: **`2025-06-18`**
   - Methods to implement: Respond to `initialize`, `ping`, `tools/list` and `tools/call`; ignore notifications
   - JSON-RPC error codes: Unknown tool name → **-32602**; Unknown method → **-32601**; Unparseable JSON → **-32700**

## Q6. What defines the "root" directory mentioned in error handling—is it the repository root, the current working directory, or something else?
A: The root directory is one fixed at startup with the `--root` flag. It is neither necessarily the repository root nor the current working directory—it is whatever directory is specified when the server starts up.

## Q7. For the four tools (git_status, git_log, git_diff_stat, rg_search), what are the parameters each tool accepts—for example, does rg_search accept a directory argument, case sensitivity flags, or only a pattern?
A: The four tools accept the following parameters:
   - `git_status`: no arguments
   - `git_log`: `limit` (an integer from 1–50, default 10)
   - `git_diff_stat`: no arguments
   - `rg_search`: `pattern` (a required non-empty string) and `path` (optional, default `.`)
   
   Any argument not listed is rejected. For example, rg_search does not accept case sensitivity flags—only a pattern and optional path.

## Q8. How should this MCP server be deployed with Claude Code—is it bundled by default, installed as a plugin, or configured by the user?
A: The user must configure it themselves. They can run `claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`, or create a project `.mcp.json` file with the same command. Either method must work. It is not bundled by default.

## Q9. Does the MCP server validate that paths in `rg_search` stay within the configured root, and what happens if a user specifies a path like `../outside` or an absolute path outside the root?
A: Yes, the MCP server validates that paths in `rg_search` stay within the configured root. A `path` that resolves outside the root (`../`, an absolute path elsewhere) is rejected with a tool error saying the path escapes the root.

## Q10. How should git operations handle authentication—should SSH keys, git credentials, and SSH config be inherited from the environment where the server runs, or is authentication out of scope?
A: Authentication is out of scope.

## Q11. What is the output format for each tool—plain text, JSON, or structured? For example, does `git_status` return plain `git status` output, or a parsed structure?
A: No decision - treat it as a non-goal.

## Q12. How should the MCP server handle symlinks in the root directory or in `rg_search` paths—should they be dereferenced (resolved to their target), followed as normal, or rejected?
A: No decision - treat it as a non-goal.

## Q13. Is the `--root` flag required when starting the server, or is it optional? If optional, what is the default?
A: No decision - treat it as a non-goal.

## Q14. If the root directory is not a valid git repository (or git is not initialized), how should `git_status`, `git_log`, and `git_diff_stat` behave—should they return an error via `isError: true`, or is this out of scope?
A: When a git command fails—such as when the root directory is not a valid git repository—it returns a normal result with `isError: true` and the reason as text, so the model can read it and adapt. This falls under the general rule for tool failures.

## Q15. For `rg_search`, does the 10-second timeout include regex pattern compilation time, or only the search execution?
A: No decision - treat it as a non-goal.
