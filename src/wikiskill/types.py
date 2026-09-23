"""Core data types.

Deliberately dependency-free dataclasses. Every type that crosses a disk or
LLM boundary carries ``to_dict``/``from_dict`` so the JSON shape is written in
one place and not re-derived at each call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .util import canonical_json, content_sha

Split = Literal["train", "val", "test"]
StepKind = Literal["reasoning", "tool_call", "tool_result", "answer", "error"]


# --------------------------------------------------------------------------
# Tasks and traces (the Raw layer)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    split: Split
    family: str
    """Stratification key. The maintainer samples across families so one noisy
    family cannot monopolise the wiki."""
    prompt: str
    env_spec: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Task":
        return cls(
            task_id=d["task_id"],
            split=d["split"],
            family=d["family"],
            prompt=d["prompt"],
            env_spec=dict(d.get("env_spec", {})),
            expected=dict(d.get("expected", {})),
        )


@dataclass(frozen=True, slots=True)
class TraceStep:
    index: int
    kind: StepKind
    text: str = ""
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "kind": self.kind,
            "text": self.text,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TraceStep":
        return cls(
            index=d["index"],
            kind=d["kind"],
            text=d.get("text", ""),
            tool_name=d.get("tool_name"),
            tool_input=d.get("tool_input"),
            tool_output=d.get("tool_output"),
        )


@dataclass(frozen=True, slots=True)
class Trace:
    """One rollout. Immutable once written -- this is the Raw layer."""

    trace_id: str
    task_id: str
    split: Split
    family: str
    iteration: int
    skillset_sha: str
    steps: tuple[TraceStep, ...]
    final_answer: str | None
    score: float
    passed: bool
    failure_summary: str | None = None
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "split": self.split,
            "family": self.family,
            "iteration": self.iteration,
            "skillset_sha": self.skillset_sha,
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "score": self.score,
            "passed": self.passed,
            "failure_summary": self.failure_summary,
            "truncated": self.truncated,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Trace":
        return cls(
            trace_id=d["trace_id"],
            task_id=d["task_id"],
            split=d["split"],
            family=d["family"],
            iteration=d["iteration"],
            skillset_sha=d["skillset_sha"],
            steps=tuple(TraceStep.from_dict(s) for s in d["steps"]),
            final_answer=d.get("final_answer"),
            score=d["score"],
            passed=d["passed"],
            failure_summary=d.get("failure_summary"),
            truncated=d.get("truncated", False),
        )

    def render(self, max_chars: int = 4000) -> str:
        """Human/LLM-readable rendering, used when a trace is shown to an agent."""
        lines = [
            f"trace {self.trace_id}  task={self.task_id}  family={self.family}",
            f"score={self.score:.2f}  passed={self.passed}",
        ]
        if self.failure_summary:
            lines.append(f"failure: {self.failure_summary}")
        for s in self.steps:
            if s.kind == "tool_call":
                payload = canonical_json(s.tool_input or {})
                lines.append(f"  [{s.index}] CALL {s.tool_name} {payload}")
            elif s.kind == "tool_result":
                lines.append(f"  [{s.index}] RESULT {s.tool_output}")
            elif s.kind == "answer":
                lines.append(f"  [{s.index}] ANSWER {s.text}")
            elif s.kind == "error":
                lines.append(f"  [{s.index}] ERROR {s.text}")
            else:
                lines.append(f"  [{s.index}] THOUGHT {s.text}")
        out = "\n".join(lines)
        return out if len(out) <= max_chars else out[: max_chars - 3] + "..."


# --------------------------------------------------------------------------
# Skills (the Skills layer)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Skill:
    """One skill directory: SKILL.md plus PURPOSE.md.

    ``purpose`` is not decoration -- it is the edge back to the wiki patterns
    that motivated the skill, which is what keeps the Skills layer auditable
    against the Wiki layer.
    """

    name: str
    description: str
    body: str
    purpose: str
    source_patterns: tuple[str, ...] = ()

    def skill_md(self) -> str:
        desc = self.description.replace("\n", " ").strip()
        return f"---\nname: {self.name}\ndescription: {desc}\n---\n\n{self.body.strip()}\n"

    def purpose_md(self) -> str:
        cited = "\n".join(f"- {p}" for p in self.source_patterns) or "- (none recorded)"
        return (
            f"# Why `{self.name}` exists\n\n{self.purpose.strip()}\n\n"
            f"## Motivating wiki patterns\n\n{cited}\n"
        )

    def nbytes(self) -> int:
        return len(self.skill_md().encode("utf-8"))


@dataclass(frozen=True, slots=True)
class SkillSet:
    """An immutable, content-addressed set of skills.

    Every mutation returns a new ``SkillSet`` with a fresh ``sha``. That purity
    is what makes rollback trivial: rejecting a proposal is "never move HEAD",
    not "undo an edit".
    """

    skills: tuple[Skill, ...] = ()

    @property
    def sha(self) -> str:
        payload = "\x00".join(
            f"{s.name}\x01{s.skill_md()}\x01{s.purpose_md()}" for s in self.sorted()
        )
        return content_sha(payload)

    def sorted(self) -> tuple[Skill, ...]:
        return tuple(sorted(self.skills, key=lambda s: s.name))

    def names(self) -> tuple[str, ...]:
        return tuple(s.name for s in self.sorted())

    def get(self, name: str) -> Skill | None:
        return next((s for s in self.skills if s.name == name), None)

    def with_skill(self, skill: Skill) -> "SkillSet":
        others = tuple(s for s in self.skills if s.name != skill.name)
        return SkillSet(skills=others + (skill,))

    def without(self, name: str) -> "SkillSet":
        return SkillSet(skills=tuple(s for s in self.skills if s.name != name))

    def total_bytes(self) -> int:
        return sum(s.nbytes() for s in self.skills)

    def render_for_prompt(self) -> str:
        """The block injected into the Inference Agent's system prompt.

        This is the ONLY channel by which accumulated experience reaches
        inference. The wiki is not rendered here and must never be.
        """
        if not self.skills:
            return "(no skills yet)"
        return "\n\n".join(
            f"### Skill: {s.name}\n{s.description.strip()}\n\n{s.body.strip()}"
            for s in self.sorted()
        )


# --------------------------------------------------------------------------
# Wiki edits and proposals
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PatchOp:
    """One incremental edit to a wiki pattern page.

    The paper specifies patch-based editing rather than rewriting, so pages
    compound across iterations instead of being flattened each time.
    """

    op: Literal["create_page", "append", "replace", "insert_after"]
    path: str
    content: str = ""
    anchor: str | None = None
    title: str | None = None
    evidence_traces: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PatchOp":
        return cls(
            op=d["op"],
            path=d["path"],
            content=d.get("content", ""),
            anchor=d.get("anchor"),
            title=d.get("title"),
            evidence_traces=tuple(d.get("evidence_traces", ())),
        )


@dataclass(frozen=True, slots=True)
class WikiEditBatch:
    edits: tuple[PatchOp, ...]
    log_entry: str


@dataclass(frozen=True, slots=True)
class Proposal:
    """One atomic skill creation or edit, targeting exactly one skill."""

    proposal_id: str
    iteration: int
    action: Literal["create", "edit"]
    target_skill: str
    rationale: str
    skill: Skill
    evidence_patterns: tuple[str, ...] = ()
    evidence_traces: tuple[str, ...] = ()
    reads: tuple[str, ...] = ()
    """Audit trail of the ReAct loop's read_file calls."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "iteration": self.iteration,
            "action": self.action,
            "target_skill": self.target_skill,
            "rationale": self.rationale,
            "evidence_patterns": list(self.evidence_patterns),
            "evidence_traces": list(self.evidence_traces),
            "reads": list(self.reads),
            "skill": {
                "name": self.skill.name,
                "description": self.skill.description,
                "body": self.skill.body,
                "purpose": self.skill.purpose,
                "source_patterns": list(self.skill.source_patterns),
            },
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Proposal":
        s = d["skill"]
        return cls(
            proposal_id=d["proposal_id"],
            iteration=d["iteration"],
            action=d["action"],
            target_skill=d["target_skill"],
            rationale=d["rationale"],
            skill=Skill(
                name=s["name"],
                description=s["description"],
                body=s["body"],
                purpose=s["purpose"],
                source_patterns=tuple(s.get("source_patterns", ())),
            ),
            evidence_patterns=tuple(d.get("evidence_patterns", ())),
            evidence_traces=tuple(d.get("evidence_traces", ())),
            reads=tuple(d.get("reads", ())),
        )


# --------------------------------------------------------------------------
# Loop bookkeeping
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IterationResult:
    iteration: int
    train_score: float
    wiki_edits_applied: int
    wiki_edits_rejected: int
    proposal: Proposal | None
    parent_sha: str
    candidate_sha: str | None
    unified_diff: str
    val_candidate: float
    val_incumbent: float
    accepted: bool
    reject_reason: str | None
    r_best_after: float
    head_after: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "train_score": self.train_score,
            "wiki_edits_applied": self.wiki_edits_applied,
            "wiki_edits_rejected": self.wiki_edits_rejected,
            "proposal": self.proposal.to_dict() if self.proposal else None,
            "parent_sha": self.parent_sha,
            "candidate_sha": self.candidate_sha,
            "unified_diff": self.unified_diff,
            "val_candidate": self.val_candidate,
            "val_incumbent": self.val_incumbent,
            "accepted": self.accepted,
            "reject_reason": self.reject_reason,
            "r_best_after": self.r_best_after,
            "head_after": self.head_after,
        }
