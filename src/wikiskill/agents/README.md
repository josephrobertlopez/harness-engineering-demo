# agents/

The three model-driven roles in the loop. Each one takes a `Backend` and a
model id, builds an `LLMRequest`, and parses the reply with `protocol.py`.
None of them writes files directly; they call the stores in
[layers/](../layers/README.md). The overview table of who sees what is in
[docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md#agents--the-three-roles).

## inference.py: the Inference Agent

`InferenceAgent.__init__(backend, model, max_steps=10)`. That is the whole
signature, and it has no wiki parameter on purpose.

**The Inference Agent never receives the wiki.** The paper's ablation found
that letting the inference agent read the wiki dropped average performance
from 63.7% to 60.9%: the agent leans on raw notes instead of the distilled
skill. A prompt line saying "do not read the wiki" would be one refactor away
from being broken. So the module does not import `layers.wiki`, and the only
learned text in its prompt is `SkillSet.render_for_prompt()`, formatted into
the `SYSTEM` template by `system_prompt`.
[tests/test_no_wiki_leak.py](../../../tests/test_no_wiki_leak.py) checks the
constructor signature, the `run` signature, the module source and the
rendered prompt. Do not add a wiki parameter "for convenience".

`run(task, env, skillset, *, iteration, raw)` is a ReAct loop of at most
`max_steps` turns. Each turn re-renders the transcript into one prompt. The
reply is parsed with `parse_thought`, `parse_answer` and `parse_action`.
A `ProtocolError` becomes an `error` step in the trace rather than an
exception, so the maintainer can see the agent lose the format. Every step is
appended through `RawStore.record_step`; the finished `Trace` is written by
`RawStore.commit`. The score comes from `starter.score`.

## maintainer.py: the Wiki Maintainer

`WikiMaintainer(backend, model, seed=0)`. `run(traces, wiki, raw, *,
iteration)` returns `(edits_applied, edits_rejected)`.

`sample` picks at most `MAX_SAMPLE` (10) traces in two passes: one trace from
every family first, then second traces for the worst-failing families.
Why two passes: a single pass that took two per family and truncated to the
budget once starved the family that sorted last, so `round_even` was never
documented and the run plateaued with nothing in the logs to say why.

The model is asked for one fenced JSON block of incremental edits
(`create_page`, `append`, `replace`, `insert_after`) plus a `log_entry`. The
batch goes to `WikiStore.apply_patch_ops` with `trace_exists=raw.exists`, so
cited evidence must resolve. If the batch fails, the model gets one repair
turn with the validator's error text. If that also fails, nothing is written
to `patterns/`, a failure note goes to the log via `append_log`, and the
iteration continues. A missed wiki edit costs less than an aborted run.

## proposer.py: the Skill Proposer

`SkillProposer(backend, model, effort="high", max_reads=8)`. `run(wiki, raw,
skillset, *, iteration, outcome_summary, context=None)` returns
`(Proposal | None, error)`.

Its standing context is thin on purpose: `wiki.index()`, `wiki.impact_log()`,
the current skill names, and the outcome summary. Full pages and traces come
only through `ACTION: read_file`, served by `_read`, which tries
`RawStore.find` and then `WikiStore.read_relative`. The read cap is
`RunConfig.proposer_max_reads`. Handing over every page would make the
proposer's context, and the bill, grow with the wiki.

The reply ends with `PROPOSAL:` and a JSON block. `_build` turns it into
exactly one `Proposal` for one `Skill`, with `action` limited to `create` or
`edit`. It checks shape only. Whether the cited patterns exist and whether an
`edit` names a real skill is checked afterwards in `EvolutionLoop.iterate`.

The proposer never reports its own outcome. `skill-impact.md` is written by
the harness (see [layers/](../layers/README.md)).
