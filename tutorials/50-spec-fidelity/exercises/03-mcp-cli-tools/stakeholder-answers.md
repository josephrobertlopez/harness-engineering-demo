# What the DevX guild said when asked

You get these answers **only by asking**. They are written down so every
learner gets the same ones and the judge can check your PRD against them.
Let the Interrogator persona (`personas/spec-interrogator.persona.md`) lead;
the Adversary (`personas/spec-adversary.persona.md`) is the one who asks
Q4 properly.

**Q1. "Git and stuff, whatever the team uses" — which CLIs, exactly?**
Two: **`git`** and **`rg`** (ripgrep). Nothing else. Not a general shell.

**Q2. Which tools does Claude see?**
Exactly four, all read-only:

| tool | runs | arguments |
|---|---|---|
| `git_status` | `git status --porcelain=v1 --branch` | none |
| `git_log` | `git log --oneline -n <limit>` | `limit`: integer 1–50, default 10 |
| `git_diff_stat` | `git diff --stat` | none |
| `rg_search` | `rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>` | `pattern`: required non-empty string; `path`: optional, default `.` |

Any argument not listed is rejected.

**Q3. Run where?**
In one root directory fixed at startup with `--root`. A `path` that resolves
outside the root (`../`, an absolute path elsewhere) is rejected with a tool
error saying the path escapes the root.

**Q4. "Should be safe" / "nothing dangerous" — concretely?**

- Commands run as an argument list; **no shell**, ever.
- Only the four commands above; no write operations (commit, checkout, push).
- A pattern starting with `-` must be searched for, not parsed as a flag
  (that is why `-e` and `--` are in the command line).
- Each command gets a **10 second** timeout.
- Output is cut at **8000 characters** with a `[truncated]` marker, so one
  huge result cannot flood the model's context.

**Q5. "Works with Claude Code" — which protocol details?**
MCP over **stdio**: newline-delimited JSON-RPC 2.0, protocol version
**`2025-06-18`**. Respond to `initialize`, `ping`, `tools/list` and
`tools/call`; ignore notifications.

- Unknown tool name → JSON-RPC error **-32602**.
- Unknown method → **-32601**. Unparseable JSON → **-32700**.
- A tool that fails — bad argument, path outside the root, missing binary,
  non-zero exit, timeout — returns a normal result with **`isError: true`**
  and the reason as text, so the model can read it and adapt.
- `rg` exiting 1 means "no matches"; that is a successful result, not an
  error.

**Q6. How does someone switch it on?**
`claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo`,
or a project `.mcp.json` with the same command. Either must work.

**Q7. Out of scope?**
Write operations, other CLIs, HTTP/SSE transport, authentication, and MCP
resources or prompts.
