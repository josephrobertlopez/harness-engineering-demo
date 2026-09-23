"""The Wiki Maintainer: compiles raw traces into compounding patterns.

Root-causes the failures, extracts what the passes did right, and emits
*incremental* edits -- append / replace / insert_after -- rather than rewriting
pages, so knowledge accumulates instead of being flattened each iteration.

Failure policy: the batch gets exactly one bounded repair turn, and if that
also fails, nothing is written to `patterns/`, a failure note goes into the
log, and **the iteration continues**. A wiki edit that does not land is a
missed learning opportunity; aborting the run over one bad JSON object is far
more expensive. The flip side is that a *partial* batch would be permanent
damage on a never-rolled-back layer, which is why application is atomic.
"""

from __future__ import annotations

import random
from collections import defaultdict

from ..backends.base import Backend, LLMRequest
from ..layers.raw import RawStore
from ..layers.wiki import WikiStore
from ..protocol import ProtocolError, parse_json_block
from ..types import PatchOp, Trace, WikiEditBatch

SYSTEM = """\
You maintain a wiki of hard-won operating knowledge about an agent's task
environment. You are given a stratified sample of execution traces: some that
passed, some that failed.

Root-cause the failures. Extract the strategies behind the passes. Then emit
incremental edits to the pattern pages -- never a full rewrite.

Reply with one fenced JSON block and nothing else:

```json
{
  "edits": [
    {"op": "create_page", "path": "patterns/<slug>.md", "title": "...",
     "content": "...", "evidence_traces": ["<trace id>"]},
    {"op": "append", "path": "patterns/<slug>.md", "content": "..."},
    {"op": "replace", "path": "patterns/<slug>.md", "anchor": "<exact text>",
     "content": "..."},
    {"op": "insert_after", "path": "patterns/<slug>.md", "anchor": "<exact text>",
     "content": "..."}
  ],
  "log_entry": "one short paragraph on what you learned this iteration"
}
```

Rules that will get an edit rejected:
- `path` must match `patterns/<lowercase-slug>.md`.
- A `create_page` must cite at least one real trace id in `evidence_traces`.
- An `anchor` must appear exactly once in the current page text.
"""

MAX_SAMPLE = 10


class WikiMaintainer:
    def __init__(self, backend: Backend, model: str, seed: int = 0) -> None:
        self.backend = backend
        self.model = model
        self.seed = seed

    def sample(self, traces: list[Trace]) -> list[Trace]:
        """Stratified over families, failures first, breadth before depth.

        Two passes, not one. A single pass that takes two traces per family
        and then truncates to the budget silently starves whichever families
        sort last -- they never reach the maintainer, so their failure mode is
        never documented, so no skill is ever proposed for them and the run
        plateaus for reasons nothing in the logs explains. Taking one trace
        from every family first guarantees coverage; second traces are a
        bonus spent on the families that are failing most.
        """
        by_family: dict[str, list[Trace]] = defaultdict(list)
        for t in traces:
            by_family[t.family].append(t)

        rng = random.Random(self.seed)
        ordered: dict[str, list[Trace]] = {}
        for family, group in by_family.items():
            group = list(group)
            rng.shuffle(group)
            group.sort(key=lambda t: (t.passed, t.task_id))  # failures first
            ordered[family] = group

        # Worst-failing families first, so they also win the second pass.
        families = sorted(
            ordered,
            key=lambda f: (-sum(1 for t in ordered[f] if not t.passed), f),
        )

        picked: list[Trace] = []
        for depth in (0, 1):
            for family in families:
                if len(picked) >= MAX_SAMPLE:
                    return picked
                group = ordered[family]
                if depth < len(group):
                    picked.append(group[depth])
        return picked

    def run(
        self,
        traces: list[Trace],
        wiki: WikiStore,
        raw: RawStore,
        *,
        iteration: int,
    ) -> tuple[int, int]:
        """Returns ``(edits_applied, edits_rejected)``."""
        sample = self.sample(traces)
        failing = _failing_families(traces)
        documented = _documented_families(wiki)
        evidence = {t.family: t.trace_id for t in sample if not t.passed}

        prompt = _render_prompt(sample, failing, wiki)
        context = {
            "failing_families": failing,
            "documented_families": sorted(documented),
            "evidence": evidence,
        }

        batch, error = self._ask(prompt, context)
        if batch is not None:
            outcome = wiki.apply_patch_ops(batch.edits, trace_exists=raw.exists)
            if outcome.ok:
                wiki.append_log(iteration, batch.log_entry)
                return len(batch.edits), 0
            error = "; ".join(msg for _, msg in outcome.errors)

            # One bounded repair turn, with the validator's own error text.
            repair = (
                f"{prompt}\n\nYour previous batch was rejected: {error}\n"
                "Emit a corrected batch. Nothing was written."
            )
            batch, error = self._ask(repair, context)
            if batch is not None:
                outcome = wiki.apply_patch_ops(batch.edits, trace_exists=raw.exists)
                if outcome.ok:
                    wiki.append_log(iteration, batch.log_entry)
                    return len(batch.edits), 0
                error = "; ".join(msg for _, msg in outcome.errors)

        wiki.append_log(iteration, f"Maintenance produced no usable edits. Errors: {error}")
        return 0, 1

    def _ask(self, prompt: str, context: dict) -> tuple[WikiEditBatch | None, str]:
        text = self.backend.complete(
            LLMRequest(
                role="maintainer",
                model=self.model,
                system=SYSTEM,
                prompt=prompt,
                max_tokens=8000,
                effort="high",
                context=context,
            )
        ).text
        try:
            payload = parse_json_block(text)
            edits = tuple(PatchOp.from_dict(e) for e in payload.get("edits", []))
            log_entry = str(payload.get("log_entry", "")).strip() or "(no summary given)"
            return WikiEditBatch(edits=edits, log_entry=log_entry), ""
        except (ProtocolError, KeyError, TypeError, ValueError) as exc:
            return None, f"unparseable maintainer output: {exc}"


def _failing_families(traces: list[Trace]) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for t in traces:
        if not t.passed:
            counts[t.family] += 1
    return [f for f, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def _documented_families(wiki) -> set[str]:
    return {path.removeprefix("patterns/").removesuffix(".md").replace("-", "_") for path in wiki.pages()}


def _render_prompt(sample: list[Trace], failing: list[str], wiki: WikiStore) -> str:
    blocks = "\n\n".join(t.render() for t in sample)
    return (
        f"## Current pattern index\n\n{wiki.index()}\n\n"
        f"## Families still failing (worst first)\n\n{', '.join(failing) or '(none)'}\n\n"
        f"## Sampled traces\n\n{blocks}\n"
    )
