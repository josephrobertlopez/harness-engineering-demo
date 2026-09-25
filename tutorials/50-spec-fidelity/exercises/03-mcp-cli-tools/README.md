# Exercise 3 — DEVX-311: an MCP server over a fixed set of CLIs

**~70 minutes.** You get [`ticket.md`](ticket.md). You hand in `prd.md`,
`openspec/changes/<id>/` and `impl/` — a stdio MCP server that gives Claude
Code four read-only tools over `git` and `rg`, and nothing else.

The hardest of the three, because the vague words hide an **attack
surface**. "Git and stuff, whatever the team uses. Should be safe." There is
a one-afternoon version of this ticket — a `run_command` tool — and the
ticket's own comment thread says how that went last time.

| file | what it is | Claude sees it? |
|---|---|---|
| `ticket.md` | the ticket, as filed | yes |
| `stakeholder-answers.md` | what the DevX guild says when asked | **no** — you are the guild |
| `rubric.json`, `HARNESS.md` | what the judges check | yes |
| `solution/` | the reference answer | **no** — until you are done |

## Work backwards first (15 min)

```bash
python tutorials/50-spec-fidelity/start.py 03 ~/fidelity/backwards-03 --with-solution
python tutorials/50-spec-fidelity/spec_fidelity.py ~/fidelity/backwards-03
```

Walk these threads backwards, test → scenario → requirement → PRD →
answer → ticket:

1. `test_flag_like_pattern`. What would `rg` do with the pattern `--files`
   if the server built `["rg", pattern, path]`? Which two tokens in the real
   argv prevent it?
2. `test_no_matches` and `test_non_zero_exit`. Why is exit status 1 a
   success for `rg` and a failure for `git`? Where does the server record
   that difference, and what would the model see if it got it wrong?
3. `test_unknown_tool` expects a JSON-RPC **error**, while
   `test_log_out_of_range` expects a **result** with `isError: true`. Find
   the design decision that explains the split.

Then connect the reference server to your own Claude Code and use it:

```bash
claude mcp add cli-tools -- python /abs/path/to/solution/impl/server.py --root /abs/path/to/any/repo
claude mcp list                  # cli-tools ... ✓ Connected
claude                           # "use cli-tools to show the last 5 commits"
claude mcp remove cli-tools
```

## Then forward (55 min)

```bash
python tutorials/50-spec-fidelity/start.py 03 ~/fidelity/devx-311
cd ~/fidelity/devx-311 && claude
```

Follow [lesson 3](../../lesson-03-the-loop.md). Bring in the Adversary
early for this one: after the PRD, ask it specifically *"what can a caller
make this server run that the PRD does not list?"*

### Hints for this ticket

- **"Git and stuff, whatever the team uses"** — make them name the
  binaries. Then make them name the subcommands. Then the arguments.
- **"Should be safe" / "nothing dangerous"** — ask for mechanisms, not
  adjectives: how commands are launched, how long they may run, how much
  output may come back, and which directories they may touch.
- **"Needs to work with Claude Code"** — ask for the protocol version, the
  transport, and how a failure should look *to the model*.

### Stdlib, or the MCP SDK?

The reference is stdlib so this repository's grading needs no install. In
your own work, the official Python SDK is the normal choice. **In SDK 2.x
`FastMCP` was renamed `MCPServer`** — most examples online still show the
old name. This is the start of the SDK version, checked against `mcp` 2.2:

```python
import subprocess
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

ROOT = Path(sys.argv[sys.argv.index("--root") + 1]).resolve()
mcp = MCPServer("cli-tools")


def _run(argv: list[str], ok=(0,)) -> str:
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=10)
    if proc.returncode not in ok:
        raise ToolError(proc.stderr.strip() or f"exit {proc.returncode}")
    return proc.stdout[:8000]


@mcp.tool()
def git_log(limit: int = 10) -> str:
    """Recent commits, one line each."""
    if not 1 <= limit <= 50:
        raise ToolError("limit must be an integer from 1 to 50")
    return _run(["git", "log", "--oneline", "-n", str(limit)])


if __name__ == "__main__":
    mcp.run()  # stdio by default
```

**A spec-versus-library conflict to raise, not paper over.** The product
owner wants an unknown tool to be JSON-RPC error `-32602` (as in the
2025-06-18 spec's own example). SDK 2.x instead returns a normal result
with `isError: true`. Your scenario test for the unknown tool will fail on
the SDK route. That is the process working: take it back to the product
owner (`/fidelity:interrogate`), and change the PRD if they accept the
SDK's behaviour -- never the test alone.

Raise the SDK's `ToolError`, not `ValueError`. A plain exception reaches the
model as *"Error executing tool git_log"*, with the reason lost. Either
implementation is judged the same way: the judge reads your tests and
`rubric.json`, not your imports. The subprocess, timeout and truncation
still need the tests the spec asks for.

## Traps in this exercise

**A pattern that is a flag.** `rg --files` lists every file instead of
searching. User input must only ever appear after `-e` or `--`.

**Paths that walk out.** `../..`, or an absolute path, turns "search this
repo" into "search this machine". Resolve the path and check it is inside
the root *before* the runner is called. The test asserts the runner was
never called, not just that an error came back.

**Protocol errors for tool failures.** Clients swallow JSON-RPC errors; the
model never sees them. A bad `limit` should come back as an `isError`
result the model can read and retry. Only "that tool or method does not
exist" is a protocol error.

**Printing to stdout.** stdout *is* the protocol channel. A stray `print`
corrupts the stream, and the client reports it as a connection failure
far from the cause.

**`bool` is an `int`.** `{"limit": true}` passes `isinstance(limit, int)`
and becomes `-n 1`. The spec's out-of-range scenario includes `true` for
this reason.

## Resources

- MCP: [specification (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18),
  [tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools),
  [stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports),
  [Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- Claude Code: [connecting MCP servers](https://code.claude.com/docs/en/mcp)
- ripgrep: [guide](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md)
- Habitat-Thinking: [constraints and enforcement](https://habitat-thinking.github.io/ai-literacy-superpowers/plugins/ai-literacy-superpowers/explanation/constraints-and-enforcement/),
  [the harness-enforcer agent](https://github.com/Habitat-Thinking/ai-literacy-superpowers/blob/main/ai-literacy-superpowers/agents/harness-enforcer.agent.md)

## Checking your work

```bash
python tutorials/50-spec-fidelity/spec_fidelity.py ~/fidelity/devx-311
python tutorials/check.py 50-spec-fidelity/03     # grades this folder, if you copy your work here
```
