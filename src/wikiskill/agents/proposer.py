"""The Skill Proposer: a bounded ReAct loop that reads the wiki on demand.

Its standing context is deliberately thin -- the pattern *index*, the
skill-impact ledger, and per-family outcome counts. Full pattern pages and raw
traces arrive only through ``read_file``, capped at
``RunConfig.proposer_max_reads``.

That is the paper's design, and it is also the cost control: handing the
proposer every page in full means its context, and the bill, grow with the
wiki. By iteration eight that is the difference between a run you can afford
and one you cannot.

Output is exactly one atomic proposal targeting exactly one skill. Referential
integrity -- does that skill exist, do those patterns resolve -- is checked by
the harness afterwards; structured output guarantees shape, never reference.
"""

from __future__ import annotations

from ..backends.base import Backend, LLMRequest
from ..layers.raw import RawStore
from ..layers.wiki import WikiStore
from ..protocol import ProtocolError, parse_action, parse_json_block, parse_thought
from ..types import Proposal, Skill, SkillSet

SYSTEM = """\
You improve an agent's skill library. You may read the wiki; the agent that
executes tasks may not -- it only ever sees the skills you write. So a rule
that stays in the wiki changes nothing. It has to land in a skill.

You may investigate first:

THOUGHT: <one line>
ACTION: read_file {"path": "patterns/<slug>.md"}

When ready, emit exactly one proposal for exactly one skill:

PROPOSAL:
```json
{
  "action": "create" | "edit",
  "target_skill": "<kebab-case name>",
  "rationale": "why this will raise the validation score",
  "evidence_patterns": ["patterns/<slug>.md"],
  "evidence_traces": [],
  "description": "one line, shown to the executing agent",
  "body": "the skill instructions themselves",
  "purpose": "which wiki patterns motivated this"
}
```

Keep skills short and imperative. Verbose skills are rejected on a byte budget
before they are ever evaluated -- the ledger above shows which past proposals
were rejected and why.
"""


class SkillProposer:
    def __init__(self, backend: Backend, model: str, effort: str = "high", max_reads: int = 8) -> None:
        self.backend = backend
        self.model = model
        self.effort = effort
        self.max_reads = max_reads

    def run(
        self,
        wiki: WikiStore,
        raw: RawStore,
        skillset: SkillSet,
        *,
        iteration: int,
        outcome_summary: str,
        context: dict | None = None,
    ) -> tuple[Proposal | None, str]:
        base = (
            f"## Pattern index\n\n{wiki.index()}\n\n"
            f"## Skill impact ledger\n\n{wiki.impact_log()}\n\n"
            f"## Current skills\n\n{', '.join(skillset.names()) or '(none)'}\n\n"
            f"## Task outcomes this iteration\n\n{outcome_summary}\n"
        )
        transcript: list[str] = [base]
        reads: list[str] = []

        ctx = dict(context or {})
        ctx.setdefault("iteration", iteration)
        ctx.setdefault("covered_families", [])
        ctx.setdefault("documented_families", [])

        for _ in range(self.max_reads + 1):
            text = self.backend.complete(
                LLMRequest(
                    role="proposer",
                    model=self.model,
                    system=SYSTEM,
                    prompt="\n".join(transcript) + "\n\nYour move:",
                    max_tokens=8000,
                    effort=self.effort,
                    context=ctx,
                )
            ).text
            transcript.append(text.strip())

            if "PROPOSAL:" in text.upper():
                try:
                    return self._build(text, iteration, skillset, reads), ""
                except (ProtocolError, KeyError, TypeError, ValueError) as exc:
                    return None, f"unparseable proposal: {exc}"

            try:
                action = parse_action(text)
            except ProtocolError as exc:
                return None, f"malformed proposer action: {exc}"

            if action is None:
                return None, "proposer emitted neither a read_file action nor a proposal"

            name, args = action
            if name != "read_file":
                transcript.append(f"SYSTEM: only read_file is available, not {name!r}.")
                continue

            path = str(args.get("path", ""))
            reads.append(path)
            transcript.append(f"OBSERVATION: {_read(wiki, raw, path)}")
            _ = parse_thought(text)

        return None, f"proposer exhausted its {self.max_reads} read budget without proposing"

    def _build(self, text: str, iteration: int, skillset: SkillSet, reads: list[str]) -> Proposal:
        payload = parse_json_block(text)
        name = str(payload["target_skill"]).strip()
        if not name:
            raise ValueError("target_skill is empty")
        patterns = tuple(str(p) for p in payload.get("evidence_patterns", []))
        skill = Skill(
            name=name,
            description=str(payload.get("description", "")).strip(),
            body=str(payload.get("body", "")).strip(),
            purpose=str(payload.get("purpose", "")).strip(),
            source_patterns=patterns,
        )
        action = str(payload.get("action", "create")).strip()
        if action not in ("create", "edit"):
            raise ValueError(f"action must be create or edit, got {action!r}")
        return Proposal(
            proposal_id=f"P{iteration:02d}",
            iteration=iteration,
            action=action,  # type: ignore[arg-type]
            target_skill=name,
            rationale=str(payload.get("rationale", "")).strip(),
            skill=skill,
            evidence_patterns=patterns,
            evidence_traces=tuple(str(t) for t in payload.get("evidence_traces", [])),
            reads=tuple(reads),
        )


def _read(wiki: WikiStore, raw: RawStore, path: str) -> str:
    """Serve one read_file call, from the wiki or from a trace id."""
    if not path:
        return "ERROR: read_file needs a path."
    trace = raw.find(path)
    if trace is not None:
        return trace.render()
    try:
        return wiki.read_relative(path)
    except (OSError, ValueError) as exc:
        return f"ERROR: {exc}"
