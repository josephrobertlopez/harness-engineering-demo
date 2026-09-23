"""The Wiki layer: compounding knowledge that is never rolled back.

This store exposes no delete and no overwrite-whole-page operation. That is
the point, not an oversight -- the paper is explicit that the wiki persists
across every iteration regardless of whether the skill proposal it produced
was accepted. Rollback physically cannot reach this layer because there is no
API by which it could.

The one consequence worth stating plainly: the wiki only grows. The paper
lists the absence of pruning as a known limitation, and this implementation
inherits it rather than quietly inventing a policy the paper did not evaluate.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from ..patching import PatchOutcome, apply_batch
from ..types import PatchOp, Proposal
from ..util import append_text, atomic_write_text, read_text_lf, safe_join


class WikiStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.patterns_dir = root / "patterns"
        self.logs_path = root / "logs.md"
        self.impact_path = root / "skill-impact.md"
        self.index_path = root / "index.md"

    # -- setup ------------------------------------------------------------

    def ensure(self) -> None:
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        if not self.logs_path.exists():
            atomic_write_text(
                self.logs_path,
                "# Evolution log\n\nAppended by the Wiki Maintainer, one entry per iteration.\n",
            )
        if not self.impact_path.exists():
            atomic_write_text(
                self.impact_path,
                "# Skill impact\n\nAppended by the harness -- never by a model. One record per "
                "proposal: target, unified diff, validation scores, and verdict.\n",
            )

    # -- reading ----------------------------------------------------------

    def pages(self) -> dict[str, str]:
        """All pattern pages keyed by their wiki-relative path."""
        return {
            f"patterns/{p.name}": read_text_lf(p)
            for p in sorted(self.patterns_dir.glob("*.md"))
        }

    def read_relative(self, relative: str) -> str:
        """Read any file under the wiki root. Backs the Proposer's read_file."""
        return read_text_lf(safe_join(self.root, relative))

    def index(self) -> str:
        """A compact catalogue of pattern pages.

        The Proposer gets this, not the full pages. Handing it every page in
        full is how the proposer's context -- and the bill -- grows without
        bound by iteration eight; it pulls the pages it actually wants through
        ``read_file`` instead.
        """
        pages = self.pages()
        if not pages:
            return "(the wiki has no pattern pages yet)"
        lines = []
        for path, text in pages.items():
            body = text.splitlines()
            title = next((ln.lstrip("# ").strip() for ln in body if ln.startswith("# ")), path)
            summary = next(
                (ln.strip() for ln in body if ln.strip() and not ln.startswith("#")),
                "",
            )
            lines.append(f"- `{path}` -- {title}: {summary[:160]}")
        return "\n".join(lines)

    def impact_log(self, max_chars: int = 6000) -> str:
        if not self.impact_path.exists():
            return "(no proposals recorded yet)"
        text = read_text_lf(self.impact_path)
        return text if len(text) <= max_chars else "..." + text[-max_chars:]

    # -- writing ----------------------------------------------------------

    def apply_patch_ops(
        self,
        ops: tuple[PatchOp, ...],
        *,
        trace_exists: Callable[[str], bool] | None = None,
    ) -> PatchOutcome:
        """Validate and apply a batch. Nothing is written unless all edits pass."""
        outcome = apply_batch(self.pages(), ops, trace_exists=trace_exists)
        if outcome.ok:
            self._write_pages(outcome.pages)
        return outcome

    def _write_pages(self, pages: Mapping[str, str]) -> None:
        for relative, text in pages.items():
            atomic_write_text(safe_join(self.root, relative), text)
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        atomic_write_text(
            self.index_path,
            "# Pattern index\n\nGenerated. Lists every page under `patterns/`.\n\n"
            + self.index()
            + "\n",
        )

    def append_log(self, iteration: int, entry: str) -> None:
        append_text(
            self.logs_path,
            f"\n## Iteration {iteration} -- {_now()}\n\n{entry.strip()}\n",
        )

    def append_skill_impact(
        self,
        *,
        iteration: int,
        proposal: Proposal | None,
        unified_diff: str,
        val_candidate: float,
        val_incumbent: float,
        accepted: bool,
        reject_reason: str | None,
    ) -> None:
        """Record one proposal's fate.

        Written programmatically by the orchestration harness, as the paper
        specifies -- a model is never asked to self-report whether its own
        proposal was accepted.
        """
        verdict = "Accepted" if accepted else "Rejected"
        target = proposal.target_skill if proposal else "(none)"
        action = proposal.action if proposal else "(none)"
        pid = proposal.proposal_id if proposal else f"P{iteration:02d}"
        patterns = ", ".join(proposal.evidence_patterns) if proposal else ""
        rationale = proposal.rationale.strip() if proposal else "no proposal produced"

        block = [
            f"\n## {pid} -- iteration {iteration} -- {verdict}",
            "",
            f"- target skill: `{target}` ({action})",
            f"- validation: candidate {val_candidate:.3f} vs incumbent {val_incumbent:.3f}",
            f"- cited patterns: {patterns or '(none)'}",
        ]
        if reject_reason:
            block.append(f"- reject reason: `{reject_reason}`")
        block += ["", f"{rationale}", "", "```diff", unified_diff.rstrip("\n") or "(no change)", "```", ""]
        append_text(self.impact_path, "\n".join(block))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
