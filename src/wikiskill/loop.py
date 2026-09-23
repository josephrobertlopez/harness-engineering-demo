"""The outer evolution loop, and the journal that makes it resumable.

Seven phases per iteration, each idempotent, in strict order:

    rollout_train -> wiki_update -> propose -> apply_candidate
                  -> eval_val -> gate_decision -> commit

The invariant that makes a crash survivable is **decide, journal, then act**.
The only irreversible action in the whole loop is moving HEAD, and it happens
strictly after the decision that justifies it is durable on disk. Everything
before that point is either content-addressed (rewriting the same bytes) or
keyed by trace id (skipping work already done).

Note what is *not* recoverable and does not need to be: the wiki is never
rolled back, so there is no wiki state to restore -- only patterns to add.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .agents.inference import InferenceAgent
from .agents.maintainer import WikiMaintainer
from .agents.proposer import SkillProposer
from .backends import get_backend
from .backends.base import Backend
from .bench import starter
from .config import RunConfig
from .gating import check_budget, decide
from .layers.raw import RawStore
from .layers.skills import SkillSetStore, load_skillset_from_dir
from .layers.wiki import WikiStore
from .types import IterationResult, SkillSet, Task, Trace
from .util import append_text, canonical_json, read_json, read_text_lf, write_json

PHASES = (
    "rollout_train",
    "wiki_update",
    "propose",
    "apply_candidate",
    "eval_val",
    "gate_decision",
    "commit",
)


class Journal:
    """Append-only record of completed phases."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def record(self, iteration: int, phase: str, data: dict | None = None) -> None:
        append_text(
            self.path,
            canonical_json({"iter": iteration, "phase": phase, "data": data or {}}) + "\n",
        )

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(ln) for ln in read_text_lf(self.path).splitlines() if ln.strip()]

    def done(self, iteration: int, phase: str) -> dict | None:
        for e in reversed(self.entries()):
            if e["iter"] == iteration and e["phase"] == phase:
                return e.get("data", {})
        return None

    def last_committed(self) -> int:
        """Highest iteration that reached its commit phase.

        Resume must start from the first *uncommitted* iteration, not from the
        last journal entry of any kind. A crash partway through iteration k
        leaves k's earlier phases journaled; keying off those would skip k
        altogether and silently produce a shorter run than an uninterrupted
        one.
        """
        return max(
            (e["iter"] for e in self.entries() if e["phase"] == "commit"),
            default=0,
        )


@dataclass(slots=True)
class Workspace:
    config: RunConfig
    raw: RawStore
    wiki: WikiStore
    skills: SkillSetStore
    journal: Journal

    @classmethod
    def open(cls, config: RunConfig) -> "Workspace":
        p = config.paths
        p.root.mkdir(parents=True, exist_ok=True)
        wiki = WikiStore(p.wiki)
        wiki.ensure()
        skills = SkillSetStore(p.snapshots, p.head, p.skills)
        skills.head()  # materializes the empty skill set on first open
        if skills.mirror_is_stale():
            # Repairs a crash between the HEAD move and the mirror rebuild.
            skills.rebuild_mirror(skills.head()["sha"])
        return cls(
            config=config,
            raw=RawStore(p.raw),
            wiki=wiki,
            skills=skills,
            journal=Journal(p.journal),
        )


class Evaluator:
    """Runs a split under a given skill set, skipping completed rollouts.

    Rollouts execute in a thread pool. They are independent by construction --
    a fresh environment per task, a separate trace file per task, and a
    content-addressed response cache whose writes are atomic -- so the only
    shared state needing a lock is the backends' counters, which have one.

    Results are returned in task order regardless of completion order, so the
    scores and the maintainer's trace sample do not depend on which rollout
    happened to finish first.
    """

    def __init__(
        self,
        agent: InferenceAgent,
        raw: RawStore,
        env_factory: Callable[[Task], object],
        concurrency: int = 4,
    ) -> None:
        self.agent = agent
        self.raw = raw
        self.env_factory = env_factory
        self.concurrency = max(1, concurrency)

    def run(self, tasks: Iterable[Task], skillset: SkillSet, iteration: int) -> list[Trace]:
        sha = skillset.sha
        ordered = list(tasks)

        # Resolve cached rollouts first, on this thread. They are file reads,
        # and doing them up front keeps the pool for work that actually calls
        # a model.
        results: dict[str, Trace] = {}
        pending: list[Task] = []
        for task in ordered:
            cached = self.raw.load(iteration, task.split, task.task_id, sha)
            if cached is not None:
                results[task.task_id] = cached
            else:
                pending.append(task)

        if pending:
            workers = min(self.concurrency, len(pending))
            if workers == 1:
                for task in pending:
                    results[task.task_id] = self._rollout(task, skillset, iteration)
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = {
                        pool.submit(self._rollout, task, skillset, iteration): task
                        for task in pending
                    }
                    for future in as_completed(futures):
                        task = futures[future]
                        # Let exceptions propagate: a rollout that dies is a
                        # harness bug, and completed traces are already on
                        # disk, so --resume picks up exactly here.
                        results[task.task_id] = future.result()

        return [results[t.task_id] for t in ordered]

    def _rollout(self, task: Task, skillset: SkillSet, iteration: int) -> Trace:
        env = self.env_factory(task)
        return self.agent.run(task, env, skillset, iteration=iteration, raw=self.raw)


def mean_score(traces: list[Trace]) -> float:
    """Fraction of tasks fully passed -- the paper's R(.)."""
    if not traces:
        return 0.0
    return sum(1.0 for t in traces if t.passed) / len(traces)


class EvolutionLoop:
    def __init__(self, config: RunConfig, backend: Backend | None = None) -> None:
        self.config = config
        self.ws = Workspace.open(config)
        cache_dir = config.paths.state / "llmcache"
        self.backend = backend or get_backend(config.backend, cache_dir=cache_dir)
        self.tasks = starter.tasks()
        self.inference = InferenceAgent(self.backend, config.inference_model, config.max_steps)
        self.maintainer = WikiMaintainer(self.backend, config.maintainer_model, config.seed)
        self.proposer = SkillProposer(
            self.backend, config.proposer_model, config.proposer_effort, config.proposer_max_reads
        )
        self.evaluator = Evaluator(
            self.inference, self.ws.raw, starter.StarterEnv, concurrency=config.concurrency
        )

    # -- helpers ----------------------------------------------------------

    def split(self, name: str) -> list[Task]:
        return [t for t in self.tasks if t.split == name]

    def _iter_state_path(self, iteration: int, name: str) -> Path:
        return self.config.paths.iter_dir(iteration) / name

    # -- baseline ---------------------------------------------------------

    def baseline(self, split: str = "val") -> float:
        """R_best before evolution: the empty skill set on the given split."""
        traces = self.evaluator.run(self.split(split), SkillSet(), iteration=0)
        return mean_score(traces)

    # -- one iteration ----------------------------------------------------

    def iterate(self, iteration: int) -> IterationResult:
        cfg = self.config
        ws = self.ws
        head = ws.skills.head()
        parent_sha = head["sha"]
        r_best = float(head.get("r_best", 0.0))
        incumbent = ws.skills.load(parent_sha)

        # -- phase 1: training rollouts with the current skills ----------
        train = self.evaluator.run(self.split("train"), incumbent, iteration)
        train_score = mean_score(train)
        ws.journal.record(iteration, "rollout_train", {"score": train_score})

        # -- phase 2: compile traces into the wiki -----------------------
        if ws.journal.done(iteration, "wiki_update") is None:
            applied, rejected = self.maintainer.run(train, ws.wiki, ws.raw, iteration=iteration)
            ws.journal.record(iteration, "wiki_update", {"applied": applied, "rejected": rejected})
        else:
            data = ws.journal.done(iteration, "wiki_update") or {}
            applied, rejected = int(data.get("applied", 0)), int(data.get("rejected", 0))

        # -- phase 3: propose one skill change ---------------------------
        proposal_path = self._iter_state_path(iteration, "proposal.json")
        if proposal_path.exists():
            from .types import Proposal

            proposal: Proposal | None = Proposal.from_dict(read_json(proposal_path))
            propose_error = ""
        else:
            proposal, propose_error = self.proposer.run(
                ws.wiki,
                ws.raw,
                incumbent,
                iteration=iteration,
                outcome_summary=starter.summarize(train),
                context=self._mock_context(iteration, incumbent),
            )
            if proposal is not None:
                write_json(proposal_path, proposal.to_dict())
        ws.journal.record(iteration, "propose", {"ok": proposal is not None, "error": propose_error})

        if proposal is None:
            return self._reject(
                iteration, incumbent, parent_sha, r_best, None, "", r_best, r_best,
                propose_error or "invalid_proposal", applied, rejected,
            )

        # -- phase 4: apply to a candidate snapshot ----------------------
        # Referential integrity: structured output guarantees shape, never
        # that the things it names exist.
        known_pages = set(ws.wiki.pages())
        dangling = [p for p in proposal.evidence_patterns if p not in known_pages]
        if dangling:
            return self._reject(
                iteration, incumbent, parent_sha, r_best, proposal, "", r_best, r_best,
                f"invalid_proposal: cites missing pattern(s) {', '.join(dangling)}",
                applied, rejected,
            )
        if proposal.action == "edit" and incumbent.get(proposal.target_skill) is None:
            return self._reject(
                iteration, incumbent, parent_sha, r_best, proposal, "", r_best, r_best,
                f"invalid_proposal: edit targets unknown skill {proposal.target_skill!r}",
                applied, rejected,
            )

        candidate = incumbent.with_skill(proposal.skill)
        diff = ws.skills.unified_diff(incumbent, candidate)

        budget_error = check_budget(
            skill_bytes=proposal.skill.nbytes(),
            skillset_bytes=candidate.total_bytes(),
            skill_budget=cfg.skill_budget_bytes,
            skillset_budget=cfg.skillset_budget_bytes,
        )
        if budget_error:
            return self._reject(
                iteration, incumbent, parent_sha, r_best, proposal, diff, r_best, r_best,
                budget_error, applied, rejected,
            )

        candidate_sha = ws.skills.materialize(candidate)
        ws.journal.record(iteration, "apply_candidate", {"sha": candidate_sha})

        # -- phase 5: paired validation ----------------------------------
        val_tasks = self.split("val")
        val_candidate = mean_score(self.evaluator.run(val_tasks, candidate, iteration))
        val_incumbent = mean_score(self.evaluator.run(val_tasks, incumbent, iteration))
        ws.journal.record(
            iteration, "eval_val", {"candidate": val_candidate, "incumbent": val_incumbent}
        )

        # -- phase 6: gate -----------------------------------------------
        decision = decide(
            val_candidate=val_candidate,
            val_incumbent=val_incumbent,
            r_best=r_best,
            margin=cfg.gate_margin,
        )
        ws.journal.record(
            iteration,
            "gate_decision",
            {"accepted": decision.accepted, "r_best": decision.r_best_after},
        )

        if not decision.accepted:
            return self._reject(
                iteration, incumbent, parent_sha, decision.r_best_after, proposal, diff,
                val_candidate, val_incumbent, decision.reason, applied, rejected,
            )

        # -- phase 7: commit (the only irreversible step) ----------------
        ws.skills.set_head(candidate_sha, iteration, decision.r_best_after)
        ws.journal.record(iteration, "commit", {"head": candidate_sha})
        ws.wiki.append_skill_impact(
            iteration=iteration,
            proposal=proposal,
            unified_diff=diff,
            val_candidate=val_candidate,
            val_incumbent=val_incumbent,
            accepted=True,
            reject_reason=None,
        )
        return IterationResult(
            iteration=iteration,
            train_score=train_score,
            wiki_edits_applied=applied,
            wiki_edits_rejected=rejected,
            proposal=proposal,
            parent_sha=parent_sha,
            candidate_sha=candidate_sha,
            unified_diff=diff,
            val_candidate=val_candidate,
            val_incumbent=val_incumbent,
            accepted=True,
            reject_reason=None,
            r_best_after=decision.r_best_after,
            head_after=candidate_sha,
        )

    # -- rejection path ---------------------------------------------------

    def _reject(
        self,
        iteration: int,
        incumbent: SkillSet,
        parent_sha: str,
        r_best: float,
        proposal,
        diff: str,
        val_candidate: float,
        val_incumbent: float,
        reason: str | None,
        applied: int,
        rejected: int,
    ) -> IterationResult:
        """Record the rejection. HEAD is not touched, and neither is the wiki.

        There is nothing to undo -- the candidate lives in its own snapshot
        that simply never becomes HEAD. The wiki keeps every pattern it
        learned this iteration, which is the point: the knowledge survives
        even when the skill built on it did not.
        """
        self.ws.skills.set_head(parent_sha, iteration, r_best)
        # Rejections reached from the gate have already journaled their
        # decision; those short-circuited earlier (invalid proposal, budget)
        # have not. Record it once either way.
        if self.ws.journal.done(iteration, "gate_decision") is None:
            self.ws.journal.record(iteration, "gate_decision", {"accepted": False, "r_best": r_best})
        self.ws.journal.record(iteration, "commit", {"head": parent_sha})
        self.ws.wiki.append_skill_impact(
            iteration=iteration,
            proposal=proposal,
            unified_diff=diff,
            val_candidate=val_candidate,
            val_incumbent=val_incumbent,
            accepted=False,
            reject_reason=reason,
        )
        return IterationResult(
            iteration=iteration,
            train_score=val_incumbent,
            wiki_edits_applied=applied,
            wiki_edits_rejected=rejected,
            proposal=proposal,
            parent_sha=parent_sha,
            candidate_sha=None,
            unified_diff=diff,
            val_candidate=val_candidate,
            val_incumbent=val_incumbent,
            accepted=False,
            reject_reason=reason,
            r_best_after=r_best,
            head_after=parent_sha,
        )

    # -- mock plumbing ----------------------------------------------------

    def _mock_context(self, iteration: int, skillset: SkillSet) -> dict:
        """Out-of-band hints for the mock backend. Never sent to a real model."""
        documented = [
            p.removeprefix("patterns/").removesuffix(".md").replace("-", "_")
            for p in self.ws.wiki.pages()
        ]
        # Ask the mock what it recognises rather than re-deriving it here.
        # Two copies of this rule silently diverged once, and the loop
        # plateaued while every individual component looked correct.
        from .backends import mock as mock_backend

        covered = mock_backend.covered_families(skillset.render_for_prompt())
        return {
            "iteration": iteration,
            "documented_families": documented,
            "covered_families": covered,
            "decoy_iteration": self.config.extra.get("decoy_iteration"),
        }

    # -- full run ---------------------------------------------------------

    def run(self, iterations: int | None = None) -> list[IterationResult]:
        total = iterations if iterations is not None else self.config.iterations
        results: list[IterationResult] = []

        head = self.ws.skills.head()
        if head.get("r_best", 0.0) == 0.0 and self.ws.journal.done(0, "baseline") is None:
            base = self.baseline("val")
            self.ws.skills.set_head(head["sha"], 0, base)
            self.ws.journal.record(0, "baseline", {"val": base})

        # Already converged: re-running must not quietly start burning
        # iterations (and tokens) past the early-stop point.
        if float(self.ws.skills.head().get("r_best", 0.0)) >= self.config.early_stop_score:
            return results

        start = self.ws.journal.last_committed() + 1
        for k in range(start, start + total):
            if self.ws.journal.done(k, "commit") is not None:
                continue
            result = self.iterate(k)
            results.append(result)
            if result.r_best_after >= self.config.early_stop_score:
                break
        return results

    # -- final evaluation -------------------------------------------------

    def evaluate(
        self,
        split: str,
        skills: str = "accepted",
        skills_dir: Path | None = None,
    ) -> tuple[float, list[Trace]]:
        """Score a split under a chosen skill set.

        `skills_dir` beats `skills`, and loads a hand-written folder rather
        than a snapshot from the store -- the path a tutorial learner takes.
        Evaluation never touches HEAD, the wiki, or the journal, so measuring
        someone's draft skill cannot corrupt a real run.
        """
        if skills_dir is not None:
            skillset = load_skillset_from_dir(skills_dir)
        elif skills == "none":
            skillset = SkillSet()
        elif skills == "accepted":
            skillset = self.ws.skills.head_skillset()
        else:
            skillset = self.ws.skills.load(skills)
        traces = self.evaluator.run(self.split(split), skillset, iteration=99)
        return mean_score(traces), traces
