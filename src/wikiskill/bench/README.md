# bench/

The benchmark the loop runs against. One module ships: `starter.py`, a
simulated records service. It exists so the repo runs offline on day one.
How to replace it with your own tasks is in
[docs/EXTENDING.md](../../../docs/EXTENDING.md); this file describes what is
here.

## starter.py

Twenty tasks: five quirk families in `FAMILIES`, four instances each. Each
family hides one rule that cannot be inferred from the prompt, only found by
failing.

| family | the rule |
|---|---|
| `iso_z` | timestamps need a `T` separator and a trailing `Z` |
| `rec_prefix` | `fetch` only accepts the canonical uppercase `REC-` id |
| `page_two` | `search` returns three hits per page; the answer is on page 2 |
| `round_even` | money rounds half-to-even at 2dp, not half-up |
| `idem_key` | the payload needs `idempotency_key` = `"<record>:<op>"` |

`_SPLIT_BY_INSTANCE` maps instances 0 and 1 to `train`, 2 to `val` and 3 to
`test`. The splits are disjoint by construction, so memorising a train answer
scores nothing on val.

### The three things a benchmark supplies

- **`tasks()`** returns the `Task` list. `family` is the stratification key
  the Wiki Maintainer samples by; `env_spec` holds `family` and `instance`;
  `expected` is what the scorer compares against.
- **`StarterEnv(task)`** is the environment. `tool_spec()` returns
  `TOOL_SPEC` (`search` and `fetch`), and `call(name, args)` returns the
  observation as text. It is built fresh per task and has no network and no
  clock, because rollouts run in a thread pool and shared state would corrupt
  traces.
- **`score(task, answer)`** returns `(score, failure_summary)`. It gives
  per-field partial credit, and a task passes only at 1.0. It is pure and
  deterministic, with no model judge: the gate is only as trustworthy as the
  scorer under it. The summary names the first wrong field, which is what the
  maintainer reads to root-cause.

`summarize(traces)` produces per-family pass counts. `EvolutionLoop.iterate`
passes it to the Skill Proposer as `outcome_summary`.

### Two quirks the environment reveals, three it does not

`rec_prefix` answers a wrong id with an error that names the canonical form,
and `page_two` returns `more_pages: true`. The other three are silent. That
split is deliberate; the live run in [docs/RESULTS.md](../../../docs/RESULTS.md)
shows a real model passing the first two unaided and failing the rest.

### Every value must discriminate

`_AMOUNTS` holds the `round_even` values. Each one rounds differently under
half-even and half-up, as the comment above it says. An earlier set had two
values that rounded the same either way, so those tasks passed without the
skill and the split carried no signal for that family.

### The mock marker

`QUIRK_TOKEN` is `[[QUIRK:{family}]]`. The mock backend looks for it in the
skill text to decide whether the simulated agent knows a rule. It is a
simulation device for the offline test. Real models read the prose; nothing
in the loop depends on the marker. See [backends/](../backends/README.md).

## How it is wired in

There is no benchmark registry. `EvolutionLoop.__init__` calls
`starter.tasks()` and passes `starter.StarterEnv` to `Evaluator`, and
`InferenceAgent.run` calls `starter.score`. `RunConfig.bench` defaults to
`"starter"` but nothing reads it. The `__init__.py` docstring mentions a
`loader` module; it does not exist.
