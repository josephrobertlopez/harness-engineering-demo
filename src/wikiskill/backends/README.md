# backends/

Every agent talks to a model through one narrow shape, defined in `base.py`:

```python
complete(LLMRequest) -> LLMResponse
```

An `LLMRequest` is a `role`, a `model`, a `system` prompt, one fully rendered
`prompt` string, `max_tokens`, an optional `effort`, and a `context` dict.
Text comes back in `LLMResponse.text`. It is this narrow because the default
backend shells out to `claude -p`, which is single-shot and takes no custom
tool schemas. Tool use is a text protocol the harness parses (see
`protocol.py`), and it behaves the same on all three backends. The summary
table is in [docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md#backends--one-narrow-interface).

## Choosing one

`get_backend(name, *, cache_dir=None, cache=True)` in `__init__.py` accepts
the names in `BACKENDS`: `claude-cli`, `mock`, `anthropic`. The CLI default is
`claude-cli`. When `cache_dir` is given, the backend is wrapped in
`CachingBackend`; `EvolutionLoop` passes `.state/llmcache`.

## base.py

`LLMRequest`, `LLMResponse`, the `Backend` protocol, and `CachingBackend`.
The cache key is `LLMRequest.cache_key()`: a content hash of role, model,
system, prompt, `max_tokens` and effort. `context` is not in the key. A hit
re-issues no model call, which is what makes resume cheap. It is not a
determinism guarantee on a cold run: Opus 5 and Sonnet 5 reject
`temperature`, so sampling cannot be pinned. Only `mock` is deterministic
cold.

## mock.py

`MockBackend` is the offline test fixture, and it is skill-sensitive. It
dispatches on `req.role`. The simulated inference agent answers correctly
only if `_knows` finds the family's rule in the system prompt: either the
`starter.QUIRK_TOKEN` marker or prose matching every pattern group in
`_PROSE_SIGNALS`. Without the rule it returns `_wrong`, the plausible
mistake. That is what lets `tests/test_e2e_mock.py` assert real improvement
and a real rejection instead of "nothing threw".

The mock maintainer and proposer read hints from `req.context`, which never
reaches a real model. `covered_families` is exported so
`EvolutionLoop._mock_context` asks the mock what it recognises instead of
keeping a second copy of the rule. The `decoy_iteration` hint makes the mock
proposer emit a skill with no rule and no marker, so the gate rejects it.

## anthropic_api.py

`AnthropicBackend` uses the official SDK (`pip install 'wikiskill[api]'`).
With no client passed it builds `anthropic.Anthropic()`, which resolves
`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` or an `ant auth login` profile. An
unset API key does not mean no credentials.

The per-model request shape is one table, `MODEL_CAPS` in `config.py`, read
through `caps_for`. `complete` applies it:

- `thinking == "adaptive"` (Opus 5, Sonnet 5): `thinking={"type": "adaptive"}`
  and, if the request has an effort, `output_config={"effort": ...}`.
- otherwise (Haiku 4.5): `thinking={"type": "enabled", "budget_tokens": N}`,
  with `N` at least 1024 and below `max_tokens`. No effort is sent.

No sampling parameters are sent to any model. An unknown model id gets the
adaptive shape, so a mistake fails with a clear 400 rather than silently
sending `temperature`. A `stop_reason` of `refusal` raises. Guarded by
`tests/test_backend_params.py`.

## claude_cli.py

`ClaudeCliBackend` runs `claude -p` and reuses the Claude Code login, so it
needs no API key. Each fix here is a scar from [CLAUDE.md](../../../CLAUDE.md):

- `resolve_executable` skips the Windows `.cmd`/`.bat`/`.ps1` shim and runs
  `node_modules/@anthropic-ai/claude-code/bin/claude.exe` when it exists. A
  batch shim mangles arguments containing `{`, `%`, quotes or newlines, which
  is every prompt here. It does not error; the model just gets garbage.
- `build_command` passes `--system-prompt`, not `--append-system-prompt`.
  Appending left Claude Code's coding-agent identity in charge, and replacing
  also drops about 25k tokens of default prompt per call.
- `--tools ""` disables built-in tools. `--allowed-tools ""` is a different
  option and disables nothing. A model with real Read and Bash can solve a
  simulated task by means the trace never records.
- `--restricted` and `--strict-mcp-config` keep settings files, hooks and
  MCP servers out of the measurement.

`_parse` reads `--output-format json` and treats non-JSON stdout as an error.
The CLI prints prose when it cannot start, and feeding that to an agent would
turn a login failure into a wrong trace and a wrong wiki pattern.
`total_cost_usd` accumulates reported cost under a lock, because rollouts run
concurrently. Covered by `tests/test_claude_cli_backend.py`.
