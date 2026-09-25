The harness-enforcer finished checking all 6 PR-scoped constraints. **3 passed, 3 failed:**

## Deterministic

| Constraint | Result |
|---|---|
| OpenSpec change is valid and traced | ✅ PASS — 1 active change, requirements trace correctly to PRD-1..8 |
| Every scenario is tested, and tests pass | ✅ PASS — 31/31 tests pass, 1:1 scenario↔test mapping, all 30 tasks ticked |
| A real MCP client can talk to it (`mcp_smoke`) | ❌ **FAIL** |

`mcp_smoke` findings (`impl/server.py`):
- `git_log {"limit": 51}` and `{"limit": 0}` are both accepted — spec caps `limit` at 1–50 (`server.py:144-146`, no range check)
- `git_status {"args": "--all"}` is accepted — `git_status` takes no parameters per PRD-5, extras should be rejected (`server.py:142-143`)

## Agent-judged

**"Spec captures intent"** — ❌ **FAIL**
- `server.py:334-336`: `except json.JSONDecodeError: pass` — on unparseable JSON the server sends **no response**, contradicting the "Unparseable JSON → JSON-RPC error -32700" scenario. The corresponding test (`test_errors.py:83-90`) never exercises `main()`'s parse path — it calls the error helper directly, so it can't catch this.
- `server.py:256-259`: the "exit code 1 counts as success" exception (meant for ripgrep per PRD-8) is applied inside the shared `run_command()` used by all four tools, silently masking real `git` errors too.
- Several tests assert less than their scenario's THEN clause (limit-count tests don't count entries, path tests don't check resolved path, truncation test checks `≤8000` not `==8000`, isError test doesn't check the reason text) — see `test_parameters.py:41-119`, `test_security.py:20-41`, `test_limits.py:36-53`, `test_errors.py:22-36`.

**"No gold-plating"** — ✅ PASS (no findings; only stdlib deps, exactly 4 tools, nothing from PRD Non-goals implemented). Minor nit: `signal`/`shlex` imported but unused (`server.py:15-16`) — not gold-plating, just dead code.

**"The command surface is exactly the spec's"** — ❌ **FAIL**
- `server.py:167`: `git log` limit is f-string-concatenated as `f"-{limit}"` with no validation. Since `limit` is caller-controlled and unvalidated, a value like `"-output=/tmp/pwned"` becomes a real `git log` flag that writes to an arbitrary file — a caller-controlled flag injection, well outside the spec's "integer 1–50" contract and the read-only/root-confined guarantees.

**Root cause tying it together**: the unvalidated `limit` parameter (`server.py:144-146`) is the single defect behind both the `mcp_smoke` failure and the command-surface failure — it's an argument-injection vector, not just an out-of-range value.
