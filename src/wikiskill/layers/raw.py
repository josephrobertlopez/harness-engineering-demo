"""The Raw layer: immutable execution traces.

One rollout produces two files:

``<task_id>.steps.jsonl``
    Appended as each step happens. A crash leaves a readable prefix, which is
    what you want when debugging why a rollout hung.
``<task_id>.trace.json``
    Written atomically, last. **Its existence is the completion marker** --
    the resume logic skips any task that has one and redoes any task that
    doesn't, so re-running a phase is idempotent rather than duplicating work.

Nothing in this module mutates or deletes an existing trace.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..types import Trace, TraceStep
from ..util import atomic_write_text, append_text, canonical_json, read_json


def trace_id(iteration: int, split: str, task_id: str, skillset_sha: str) -> str:
    """Stable, derivable key.

    The skill-set sha is load-bearing: within one iteration the same task is
    evaluated under both the incumbent and the candidate, and those two traces
    must not collide. Deriving the id rather than counting means it survives a
    crash and resume unchanged.
    """
    return f"i{iteration:02d}-{split}-{task_id}-{skillset_sha[:8]}"


class RawStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    # -- paths ------------------------------------------------------------

    def bucket(self, iteration: int, split: str, skillset_sha: str) -> Path:
        # Bucketing by skill-set sha is required, not cosmetic: within one
        # iteration the same validation task is run under both the incumbent
        # and the candidate, and the two rollouts must not overwrite each
        # other.
        return self.root / f"iter-{iteration:02d}" / split / skillset_sha[:8]

    def trace_path(self, iteration: int, split: str, task_id: str, skillset_sha: str) -> Path:
        return self.bucket(iteration, split, skillset_sha) / f"{task_id}.trace.json"

    def steps_path(self, iteration: int, split: str, task_id: str, skillset_sha: str) -> Path:
        return self.bucket(iteration, split, skillset_sha) / f"{task_id}.steps.jsonl"

    # -- writing ----------------------------------------------------------

    def begin(self, iteration: int, split: str, task_id: str, skillset_sha: str) -> None:
        """Quarantine a previous crashed attempt, if any.

        A ``.steps.jsonl`` with no ``.trace.json`` means the process died
        mid-rollout. Rollouts are cheap, so it is redone from scratch rather
        than resumed mid-conversation; the partial is kept for inspection.
        """
        steps = self.steps_path(iteration, split, task_id, skillset_sha)
        if steps.exists():
            n = 0
            while True:
                dest = steps.with_suffix(f".jsonl.crashed-{n}")
                if not dest.exists():
                    steps.rename(dest)
                    break
                n += 1

    def record_step(
        self, iteration: int, split: str, task_id: str, skillset_sha: str, step: TraceStep
    ) -> None:
        append_text(
            self.steps_path(iteration, split, task_id, skillset_sha),
            canonical_json(step.to_dict()) + "\n",
        )

    def commit(self, trace: Trace) -> Path:
        path = self.trace_path(trace.iteration, trace.split, trace.task_id, trace.skillset_sha)
        atomic_write_text(path, canonical_json(trace.to_dict()) + "\n")
        return path

    # -- reading ----------------------------------------------------------

    def load(self, iteration: int, split: str, task_id: str, skillset_sha: str) -> Trace | None:
        path = self.trace_path(iteration, split, task_id, skillset_sha)
        if not path.exists():
            return None
        return Trace.from_dict(read_json(path))

    def iter_all(self) -> Iterator[Trace]:
        for path in sorted(self.root.rglob("*.trace.json")):
            yield Trace.from_dict(read_json(path))

    def exists(self, tid: str) -> bool:
        """Whether a trace id resolves. Used to validate cited evidence."""
        return any(t.trace_id == tid for t in self.iter_all())

    def find(self, tid: str) -> Trace | None:
        return next((t for t in self.iter_all() if t.trace_id == tid), None)
